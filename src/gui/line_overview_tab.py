from bisect import bisect_right

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSlider, QSizePolicy
)

from src.gui.station_animation_widget import StationAnimationWidget
from src.model.station_numbering import display_station_id


class LineOverviewCanvas(QWidget):
    """Single-X-axis animated overview of manipulators and process baths."""

    time_selected = Signal(float)
    MARGIN_X = 46
    TRACK_Y_RATIO = 0.29
    BATH_TOP_RATIO = 0.52

    COLORS = {
        1: QColor("#2474d2"), 2: QColor("#e68a00"),
        3: QColor("#7b4acb"), 4: QColor("#15966f"),
    }

    def __init__(self, configuration, state_resolver, parent=None):
        super().__init__(parent)
        self.configuration = configuration
        self.state_resolver = state_resolver
        self.result = None
        self.current_time = 0.0
        self._segments = {}
        self._starts = {}
        self.setMinimumHeight(430)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def set_result(self, result):
        self.result = result
        grouped = {}
        for segment in getattr(result, "timeline_segments", []):
            grouped.setdefault(int(segment.manipulator_id), []).append(segment)
        self._segments = {}
        self._starts = {}
        for manipulator_id, segments in grouped.items():
            ordered = sorted(segments, key=lambda item: float(item.start_time))
            self._segments[manipulator_id] = ordered
            self._starts[manipulator_id] = [float(item.start_time) for item in ordered]
        self.update()

    def set_time(self, value):
        self.current_time = max(0.0, float(value))
        self.update()

    def _station_ids(self):
        ids = [
            int(item.id) for item in getattr(self.configuration, "stations", [])
            if bool(getattr(item, "enabled", True))
        ]
        ids=sorted(ids)
        if ids:
            low=min(ids); high=max(ids)
            ids=list(range(low, max(high,24)+1))
        else:
            ids=list(range(1,25))
        return ids

    def _x_for_position(self, position):
        ids = self._station_ids()
        left, right = min(ids), max(ids)
        usable = max(1.0, self.width() - 2 * self.MARGIN_X)
        if right == left:
            return self.MARGIN_X + usable / 2.0
        return self.MARGIN_X + (float(position) - left) / (right - left) * usable

    def _segment_at(self, manipulator_id):
        segments = self._segments.get(int(manipulator_id), ())
        starts = self._starts.get(int(manipulator_id), ())
        if not segments:
            return None
        index = bisect_right(starts, self.current_time) - 1
        if index < 0:
            return None
        segment = segments[index]
        if self.current_time <= float(segment.end_time) + 1e-9:
            return segment
        return segment

    def _next_motion_target(self, manipulator_id):
        for segment in self._segments.get(int(manipulator_id), ()):
            if float(segment.end_time) + 1e-9 < self.current_time:
                continue
            if abs(float(segment.end_position) - float(segment.start_position)) > 1e-9:
                return int(round(float(segment.end_position)))
        return None

    def _program_status_text(self, manipulator_id):
        if self.result is None:
            return ""
        mid = int(manipulator_id)
        now = self.current_time
        for wait in getattr(self.result, "consult_waits", []) or []:
            if int(wait.get("manipulator_id", -1)) != mid:
                continue
            start = float(wait.get("start_time", 0.0)); end = float(wait.get("end_time", start))
            if start <= now <= end + 1e-9:
                return (f"IDX {int(wait.get('source_plc_index', 0))}  "
                        f"cons (M{int(wait.get('target_manipulator_id', 0))}:"
                        f"{int(wait.get('target_plc_index', 0))})")
        for word in getattr(self.result, "program_word_executions", []) or []:
            if int(getattr(word, "manipulator_id", -1)) != mid:
                continue
            start=float(word.start_time); end=float(word.end_time)
            if start <= now <= end + 1e-9:
                index=int(getattr(word, "plc_index", 0))
                kind=str(getattr(word, "word_kind", "")).upper()
                if kind == "WAIT":
                    return f"IDX {index}  WAIT {max(0.0, now-start):.1f}/{max(0.0, end-start):.1f}s"
                return f"IDX {index}"
        return ""

    @staticmethod
    def _vertical_durations(manipulator, segment):
        duration = max(0.0, float(segment.end_time) - float(segment.start_time))
        lift = max(0.0, float(getattr(manipulator, "lift_time", 0.0) or 0.0))
        drop = max(0.0, float(getattr(manipulator, "drop_time", 0.0) or 0.0))
        if lift + drop > duration and lift + drop > 0.0:
            scale = duration / (lift + drop)
            lift *= scale
            drop *= scale
        return lift, drop

    def _position_at(self, manipulator):
        segment = self._segment_at(manipulator.id)
        if segment is None:
            return float(getattr(manipulator, "position", 1)), None
        start, end = float(segment.start_time), float(segment.end_time)
        p0, p1 = float(segment.start_position), float(segment.end_position)
        if str(getattr(segment, "segment_type", "")) == "loaded_move":
            lift, drop = self._vertical_durations(manipulator, segment)
            move_start = start + lift
            move_end = end - drop
            if self.current_time <= move_start:
                return p0, segment
            if self.current_time >= move_end:
                return p1, segment
            start, end = move_start, move_end
        if end <= start or self.current_time >= end:
            return p1, segment
        ratio = min(1.0, max(0.0, (self.current_time - start) / (end - start)))
        return p0 + (p1 - p0) * ratio, segment

    def _hoist_state(self, manipulator, segment):
        if segment is None:
            return "DÓŁ", False, 0.0, "PUSTY"
        loaded = (
            str(getattr(segment, "segment_type", "")) == "loaded_move"
            and getattr(segment, "hanger_id", None) is not None
        )
        if not loaded:
            return "DÓŁ", False, 0.0, "PUSTY"
        start, end = float(segment.start_time), float(segment.end_time)
        lift, drop = self._vertical_durations(manipulator, segment)
        if lift > 0.0 and self.current_time < start + lift:
            progress = (self.current_time - start) / lift
            return "PODNOSZENIE", True, min(1.0, max(0.0, progress)), "PODNOSZENIE"
        if drop > 0.0 and self.current_time > end - drop:
            progress = (end - self.current_time) / drop
            return "OPUSZCZANIE", True, min(1.0, max(0.0, progress)), "OPUSZCZANIE"
        return "GÓRA", True, 1.0, "TRANSPORT"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#f5f7fa"))
        track_y = int(self.height() * self.TRACK_Y_RATIO)
        bath_top = int(self.height() * self.BATH_TOP_RATIO)
        painter.setPen(QPen(QColor("#334155"), 4))
        painter.drawLine(self.MARGIN_X, track_y, self.width() - self.MARGIN_X, track_y)
        painter.setPen(QColor("#475569"))
        painter.drawText(self.MARGIN_X, 25, "Wspólny tor manipulatorów")

        occupancy = self.state_resolver._occupancy_at(self.current_time)
        station_map = {
            int(item.id): item for item in getattr(self.configuration, "stations", [])
        }
        ids = self._station_ids()
        pitch = (self.width() - 2 * self.MARGIN_X) / max(1, len(ids) - 1)
        card_width = max(30, min(76, int(pitch * 0.88)))
        for station_id in ids:
            station = station_map.get(station_id)
            if station is None:
                continue
            x = int(self._x_for_position(station_id))
            rect_x = x - card_width // 2
            item = occupancy.get(station_id)
            if not bool(getattr(station, "enabled", True)):
                fill = QColor("#d1d5db")
            elif item is None:
                fill = QColor("#e5e7eb")
            else:
                elapsed = float(item.get("elapsed", 0.0))
                max_time = float(getattr(station, "max_process_time", 0.0) or 0.0)
                min_time = float(getattr(station, "min_process_time", 0.0) or 0.0)
                if max_time > 0 and elapsed > max_time:
                    fill = QColor("#ff9c9c")
                elif max_time > 0 and elapsed >= 0.8 * max_time:
                    fill = QColor("#fff0a6")
                elif min_time > 0 and elapsed < min_time:
                    fill = QColor("#c9e8ff")
                else:
                    fill = QColor("#b7f0b1")
            painter.setPen(QPen(QColor("#334155"), 1))
            painter.setBrush(fill)
            painter.drawRoundedRect(rect_x, bath_top, card_width, 118, 4, 4)
            painter.setPen(QColor("#0f172a"))
            font = painter.font(); font.setBold(True); font.setPointSize(8); painter.setFont(font)
            painter.drawText(rect_x + 2, bath_top + 17, card_width - 4, 16,
                             Qt.AlignCenter, f"ST{display_station_id(station_id)}")
            font.setBold(False); font.setPointSize(7); painter.setFont(font)
            painter.drawText(rect_x + 3, bath_top + 35, card_width - 6, 32,
                             Qt.AlignCenter | Qt.TextWordWrap,
                             str(getattr(station, "name", ""))[:18])
            if item is None:
                hanger_text, time_text = "–", "wolna"
            else:
                hanger_text = f"H{item.get("hanger_id", "?")}"
                elapsed=float(item.get("elapsed",0.0))
                hardmin=float(getattr(station,"possible_min_time",getattr(station,"min_process_time",0.0)) or 0.0)
                hardmax=float(getattr(station,"possible_max_time",getattr(station,"max_process_time",0.0)) or 0.0)
                time_text = f"{hardmin:.0f}/{elapsed:.0f}/{hardmax:.0f}"
            font.setBold(True); painter.setFont(font)
            painter.drawText(rect_x + 2, bath_top + 72, card_width - 4, 18,
                             Qt.AlignCenter, hanger_text)
            painter.drawText(rect_x + 2, bath_top + 94, card_width - 4, 18,
                             Qt.AlignCenter, time_text)
            painter.setPen(QPen(QColor("#94a3b8"), 1, Qt.DotLine))
            painter.drawLine(x, track_y + 6, x, bath_top)

        manipulator_drawn = []
        for manipulator in sorted(
            getattr(self.configuration, "manipulators", []), key=lambda item: int(item.id)
        ):
            position, segment = self._position_at(manipulator)
            x = self._x_for_position(position)
            width_positions = max(0.2, float(getattr(manipulator, "manipulator_width", 2.0)))
            px_per_position = (
                self._x_for_position(min(ids) + 1) - self._x_for_position(min(ids))
                if len(ids) > 1 else 40.0
            )
            width_px = max(32, int(abs(px_per_position) * width_positions))
            left = int(x - width_px / 2)
            top = track_y - 58
            lift_state, loaded, hoist_progress, hoist_phase = self._hoist_state(manipulator, segment)
            color = self.COLORS.get(int(manipulator.id), QColor("#64748b"))
            manipulator_drawn.append((int(manipulator.id), position, width_positions, left, width_px))
            beam_height = 18
            frame_bottom = track_y - 3
            painter.setPen(QPen(color.darker(145), 2))
            painter.setBrush(color)
            painter.drawRect(left, top, width_px, beam_height)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(color, 5))
            painter.drawLine(left + 3, top + beam_height, left + 3, frame_bottom)
            painter.drawLine(left + width_px - 3, top + beam_height,
                             left + width_px - 3, frame_bottom)

            painter.setPen(Qt.white)
            font = painter.font(); font.setBold(True); font.setPointSize(9); painter.setFont(font)
            painter.drawText(left, top, width_px, beam_height, Qt.AlignCenter,
                             f"M{manipulator.id}")
            target = self._next_motion_target(manipulator.id)
            planned = f"→ST{display_station_id(target)}" if target is not None else ""
            program_status = self._program_status_text(manipulator.id)
            overlay = "  ".join(item for item in (planned, program_status) if item)
            if overlay:
                painter.setPen(QColor("#0f172a"))
                label_font = painter.font(); label_font.setBold(True); label_font.setPointSize(8)
                painter.setFont(label_font)
                painter.drawText(left - 55, top - 24, width_px + 110, 20,
                                 Qt.AlignCenter, overlay)

            travel_top = top + beam_height + 10
            travel_bottom = frame_bottom - 8
            trolley_y = int(travel_bottom - hoist_progress * (travel_bottom - travel_top))
            trolley_half = max(10, min(22, width_px // 4))
            rope_offset = max(5, min(10, trolley_half // 2))
            painter.setPen(QPen(QColor("#111827"), 2))
            painter.drawLine(int(x) - trolley_half, trolley_y,
                             int(x) + trolley_half, trolley_y)
            painter.drawLine(int(x) - rope_offset, top + beam_height,
                             int(x) - rope_offset, trolley_y)
            painter.drawLine(int(x) + rope_offset, top + beam_height,
                             int(x) + rope_offset, trolley_y)
            painter.drawLine(int(x) - trolley_half, trolley_y + 4,
                             int(x) + trolley_half, trolley_y + 4)

            hanger = getattr(segment, "hanger_id", None) if loaded else None
            state_color = QColor("#f59e0b") if hoist_phase in (
                "PODNOSZENIE", "OPUSZCZANIE"
            ) else (QColor("#22c55e") if lift_state == "GÓRA" else QColor("#ef4444"))
            painter.setBrush(state_color)
            painter.setPen(QPen(QColor("#111827"), 1))
            painter.drawEllipse(int(x) - 4, trolley_y - 4, 8, 8)

            font.setPointSize(7); font.setBold(True); painter.setFont(font)
            painter.setPen(color.darker(170))
            painter.drawText(left, frame_bottom + 4, width_px, 15,
                             Qt.AlignCenter, lift_state)

            if hanger is not None:
                load_width = max(24, min(42, width_px - 14))
                load_height = 30
                load_left = int(x) - load_width // 2
                load_top = min(frame_bottom - load_height - 2, trolley_y + 7)
                painter.setBrush(QColor("#f8fafc"))
                painter.setPen(QPen(QColor("#111827"), 1))
                painter.drawRect(load_left, load_top, load_width, load_height)
                painter.drawText(load_left, load_top, load_width, load_height,
                                 Qt.AlignCenter, f"H{hanger}")

        required_spacing = float(getattr(self.configuration, "minimum_manipulator_spacing", 0.0))
        for left_item, right_item in zip(manipulator_drawn, manipulator_drawn[1:]):
            gap = abs(right_item[1] - left_item[1])
            if gap + 1e-9 < required_spacing:
                x1 = int(self._x_for_position(left_item[1]))
                x2 = int(self._x_for_position(right_item[1]))
                painter.setPen(QPen(QColor("#dc2626"), 5))
                painter.drawLine(x1, track_y + 12, x2, track_y + 12)
                painter.setPen(QColor("#b91c1c"))
                painter.drawText(min(x1, x2), track_y + 31, abs(x2 - x1), 18,
                                 Qt.AlignCenter, f"KOLIZJA / odstęp {gap:.2f}")

        painter.setPen(QColor("#334155"))
        painter.drawText(self.MARGIN_X, self.height() - 16,
                         f"t = {self.current_time:.1f} s   |   szerokość manipulatora: parametr manipulator_width, domyślnie 2")


class LineOverviewTab(QWidget):
    """Real-time, accelerated and scrub-capable digital line overview."""

    def __init__(self, configuration):
        super().__init__()
        self.configuration = configuration
        self.result = None
        self.current_time = 0.0
        self.playing = False
        self.speed = 1.0
        self._last_tick_ms = None
        self.state_resolver = StationAnimationWidget(configuration)
        self.state_resolver.hide()
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.play_button = QPushButton("▶ Odtwarzaj")
        self.play_button.clicked.connect(self._toggle_play)
        toolbar.addWidget(self.play_button)
        toolbar.addWidget(QLabel("Prędkość:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1x", "2x", "5x", "10x", "20x", "50x", "100x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.currentTextChanged.connect(self._speed_changed)
        toolbar.addWidget(self.speed_combo)
        self.time_label = QLabel("t = 0.0 s")
        self.time_label.setMinimumWidth(120)
        toolbar.addWidget(self.time_label)
        toolbar.addStretch()
        reset_button = QPushButton("⏮ Początek")
        reset_button.clicked.connect(lambda: self.set_time(0.0))
        toolbar.addWidget(reset_button)
        layout.addLayout(toolbar)
        self.canvas = LineOverviewCanvas(self.configuration, self.state_resolver)
        layout.addWidget(self.canvas, 1)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 10000)
        self.slider.valueChanged.connect(self._slider_changed)
        layout.addWidget(self.slider)

    def update_result(self, result):
        self.result = result
        self.state_resolver.update_result(result)
        self.canvas.set_result(result)
        self.set_time(0.0)

    def set_time(self, value):
        final_time = max(0.0, float(getattr(self.result, "final_time", 0.0) or 0.0))
        self.current_time = min(max(0.0, float(value)), final_time if final_time > 0 else float(value))
        self.state_resolver.update_time(self.current_time)
        self.canvas.set_time(self.current_time)
        self.time_label.setText(f"t = {self.current_time:.1f} s")
        if final_time > 0:
            self.slider.blockSignals(True)
            self.slider.setValue(round(self.current_time / final_time * self.slider.maximum()))
            self.slider.blockSignals(False)

    def _toggle_play(self):
        self.playing = not self.playing
        self.play_button.setText("⏸ Pauza" if self.playing else "▶ Odtwarzaj")
        self._last_tick_ms = None

    def _speed_changed(self, text):
        self.speed = float(text.rstrip("x"))

    def _slider_changed(self, value):
        final_time = float(getattr(self.result, "final_time", 0.0) or 0.0)
        if final_time > 0:
            self.set_time(final_time * value / self.slider.maximum())

    def _tick(self):
        if not self.playing or self.result is None:
            self._last_tick_ms = None
            return
        now = self.timer.remainingTime()
        # QTimer interval is deterministic enough for simulation playback.
        delta = self.timer.interval() / 1000.0
        self.set_time(self.current_time + delta * self.speed)
        final_time = float(getattr(self.result, "final_time", 0.0) or 0.0)
        if final_time > 0 and self.current_time >= final_time:
            self.playing = False
            self.play_button.setText("▶ Odtwarzaj")
