from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QDoubleSpinBox,
    QComboBox,
    QGraphicsView,
    QGraphicsScene,
    QSlider,
    QCheckBox,
    QSizePolicy,
    QSplitter
)

from PySide6.QtCore import (
    Qt,
    QTimer,
    QPointF,
    QLineF,
    Signal,
    QSize
)

from PySide6.QtGui import (
    QPen,
    QBrush,
    QColor,
    QFont,
    QPolygonF,
    QPainter,
    QMouseEvent
)

from src.gui.station_animation_widget import (
    StationAnimationWidget
)


class DualTimeSlider(QWidget):
    valuesChanged = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._minimum = 0
        self._maximum = 10000
        self._lower = 2500
        self._upper = 7500
        self._active_handle = None
        self.setMinimumHeight(30)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)

    def sizeHint(self):
        return QSize(400, 30)

    def setRange(self, minimum, maximum):
        self._minimum = int(minimum)
        self._maximum = max(int(maximum), self._minimum + 1)
        self.setValues(self._lower, self._upper)

    def setValues(self, lower, upper):
        lower = max(self._minimum, min(self._maximum, int(lower)))
        upper = max(self._minimum, min(self._maximum, int(upper)))
        changed = lower != self._lower or upper != self._upper
        self._lower = lower
        self._upper = upper
        self.update()
        if changed:
            self.valuesChanged.emit(self._lower, self._upper)

    def values(self):
        return self._lower, self._upper

    def _track_bounds(self):
        radius = 8
        return radius + 2, max(radius + 3, self.width() - radius - 2)

    def _value_to_x(self, value):
        left, right = self._track_bounds()
        ratio = (value - self._minimum) / max(1, self._maximum - self._minimum)
        return left + ratio * (right - left)

    def _x_to_value(self, x):
        left, right = self._track_bounds()
        ratio = (float(x) - left) / max(1.0, right - left)
        ratio = max(0.0, min(1.0, ratio))
        return int(round(self._minimum + ratio * (self._maximum - self._minimum)))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        left, right = self._track_bounds()
        y = self.height() // 2
        painter.setPen(QPen(QColor(150, 150, 150), 3))
        painter.drawLine(int(left), y, int(right), y)
        x1 = self._value_to_x(self._lower)
        x2 = self._value_to_x(self._upper)
        painter.setPen(QPen(QColor(70, 110, 210), 4))
        painter.drawLine(int(min(x1, x2)), y, int(max(x1, x2)), y)
        for x, color, label in [
            (x1, QColor(30, 110, 220), "A"),
            (x2, QColor(180, 50, 180), "B")
        ]:
            painter.setPen(QPen(QColor(35, 35, 35), 1))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(x, y), 8, 8)
            painter.setPen(QPen(color, 1))
            painter.drawText(int(x - 4), 11, label)

    def mousePressEvent(self, event: QMouseEvent):
        x = event.position().x()
        lower_distance = abs(x - self._value_to_x(self._lower))
        upper_distance = abs(x - self._value_to_x(self._upper))
        self._active_handle = "lower" if lower_distance <= upper_distance else "upper"
        self._move_active_handle(x)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._active_handle is not None:
            self._move_active_handle(event.position().x())

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._active_handle = None

    def _move_active_handle(self, x):
        value = self._x_to_value(x)
        if self._active_handle == "lower":
            self.setValues(value, self._upper)
        elif self._active_handle == "upper":
            self.setValues(self._lower, value)


class ManipulatorTrajectoryTab(QWidget):

    SLIDER_MAX = 10000

    SOURCE_EVENT = "event"
    SOURCE_PROGRAM = "program"
    SOURCE_OVERLAY = "overlay"

    def __init__(
        self,
        configuration
    ):
        super().__init__()

        self.configuration = (
            configuration
        )

        self.event_result = None
        self.program_result = None

        #
        # Zostawiamy self.result jako alias dla kompatybilności
        # ze starszym kodem, ale wewnętrznie używamy _active_result().
        #
        self.result = None

        self.current_time = 0.0
        self.animation_running = False

        self.timer = QTimer()
        self.timer.timeout.connect(
            self._animation_step
        )

        self.margin_left = 140
        self.margin_right = 40
        self.margin_top = 40
        self.margin_bottom = 50

        self.scene_width = 1400
        self.scene_height = 760
        self.show_cycle_markers = True
        self.program_cycle_index = 0
        self.program_cycle_windows = []
        self.manipulator_colors = {
            1: QColor(
                40,
                110,
                220
            ),
            2: QColor(
                30,
                150,
                80
            ),
            3: QColor(
                220,
                90,
                40
            ),
            4: QColor(
                160,
                80,
                200
            )
        }

        self._build_ui()
        self._reset_measurement_slider()

    def _build_ui(
        self
    ):
        layout = QVBoxLayout()

        controls = QHBoxLayout()

        controls.addWidget(
            QLabel(
                "Źródło"
            )
        )

        self.source_mode = QComboBox()
        self.source_mode.addItem(
            "EventDriven",
            self.SOURCE_EVENT
        )
        self.source_mode.addItem(
            "ProgramDriven",
            self.SOURCE_PROGRAM
        )
        self.source_mode.addItem(
            "Overlay",
            self.SOURCE_OVERLAY
        )
        self.source_mode.currentIndexChanged.connect(
            self._source_changed
        )
        controls.addWidget(
            self.source_mode
        )

        controls.addWidget(
            QLabel(
                "Start [s]"
            )
        )

        self.start_time = QDoubleSpinBox()
        self.start_time.setMinimum(
            0.0
        )
        self.start_time.setMaximum(
            9999999.0
        )
        self.start_time.setDecimals(
            1
        )
        self.start_time.setSingleStep(
            10.0
        )
        self.start_time.valueChanged.connect(
            self._window_changed
        )
        controls.addWidget(
            self.start_time
        )

        controls.addWidget(
            QLabel(
                "Koniec [s]"
            )
        )

        self.end_time = QDoubleSpinBox()
        self.end_time.setMinimum(
            0.0
        )
        self.end_time.setMaximum(
            9999999.0
        )
        self.end_time.setDecimals(
            1
        )
        self.end_time.setSingleStep(
            10.0
        )
        self.end_time.valueChanged.connect(
            self._window_changed
        )
        controls.addWidget(
            self.end_time
        )

        controls.addWidget(
            QLabel(
                "Prędkość"
            )
        )

        self.speed = QComboBox()
        self.speed.addItem(
            "1x",
            1.0
        )
        self.speed.addItem(
            "2x",
            2.0
        )
        self.speed.addItem(
            "5x",
            5.0
        )
        self.speed.addItem(
            "10x",
            10.0
        )
        self.speed.addItem(
            "25x",
            25.0
        )
        self.speed.addItem(
            "50x",
            50.0
        )
        self.speed.addItem(
            "100x",
            100.0
        )
        self.speed.setCurrentIndex(
            3
        )
        controls.addWidget(
            self.speed
        )

        self.play_button = QPushButton(
            "Play"
        )
        self.play_button.clicked.connect(
            self.toggle_animation
        )
        controls.addWidget(
            self.play_button
        )

        self.reset_button = QPushButton(
            "Reset"
        )
        self.reset_button.clicked.connect(
            self.reset_animation
        )
        controls.addWidget(
            self.reset_button
        )

        self.steady_button = QPushButton(
            "Ustaw stan ustalony"
        )
        self.steady_button.clicked.connect(
            self.set_steady_state_window
        )
        controls.addWidget(
            self.steady_button
        )

        self.fit_all_button = QPushButton(
            "Całość"
        )
        self.fit_all_button.clicked.connect(
            self.set_full_window
        )
        controls.addWidget(
            self.fit_all_button
        )
        self.previous_cycle_button = QPushButton(
            "<< Cykl"
        )

        self.previous_cycle_button.clicked.connect(
            self.go_to_previous_cycle
        )

        controls.addWidget(
            self.previous_cycle_button
        )

        self.next_cycle_button = QPushButton(
            "Cykl >>"
        )

        self.next_cycle_button.clicked.connect(
            self.go_to_next_cycle
        )

        controls.addWidget(
            self.next_cycle_button
        )

        self.cycle_label = QLabel(
            "Cykl: -"
        )
        controls.addWidget(
            QLabel(
                "Zakres:"
            )
        )

        self.cycle_span = QComboBox()

        for count in [
            1,
            2,
            3,
            5,
            10
        ]:
            self.cycle_span.addItem(
                str(count),
                count
            )

        self.cycle_span.setCurrentIndex(
            0
        )

        self.cycle_span.currentIndexChanged.connect(
            self._cycle_span_changed
        )

        controls.addWidget(
            self.cycle_span
        )

        controls.addWidget(
            self.cycle_label
        )

        self.show_plc_indexes = QCheckBox(
            "Indeksy PLC"
        )
        self.show_plc_indexes.setChecked(True)
        self.show_plc_indexes.stateChanged.connect(
            self.draw
        )
        controls.addWidget(
            self.show_plc_indexes
        )

        self.toggle_station_animation_button = QPushButton(
            "Ukryj czasy wanien"
        )
        self.toggle_station_animation_button.clicked.connect(
            self._toggle_station_animation
        )
        controls.addWidget(
            self.toggle_station_animation_button
        )

        layout.addLayout(
            controls
        )

        time_controls = QHBoxLayout()

        time_controls.addWidget(
            QLabel(
                "Czas animacji [s]"
            )
        )

        self.time_slider = QSlider(
            Qt.Horizontal
        )
        self.time_slider.setMinimum(
            0
        )
        self.time_slider.setMaximum(
            self.SLIDER_MAX
        )
        self.time_slider.valueChanged.connect(
            self._slider_changed
        )
        time_controls.addWidget(
            self.time_slider
        )

        self.time_spin = QDoubleSpinBox()
        self.time_spin.setMinimum(
            0.0
        )
        self.time_spin.setMaximum(
            9999999.0
        )
        self.time_spin.setDecimals(
            1
        )
        self.time_spin.setSingleStep(
            1.0
        )
        self.time_spin.valueChanged.connect(
            self._time_spin_changed
        )
        time_controls.addWidget(
            self.time_spin
        )

        layout.addLayout(
            time_controls
        )

        measure_controls = QHBoxLayout()
        measure_controls.addWidget(
            QLabel("Pomiar czasu A/B")
        )
        self.measure_slider = DualTimeSlider()
        self.measure_slider.valuesChanged.connect(
            self._measurement_slider_changed
        )
        measure_controls.addWidget(
            self.measure_slider,
            1
        )
        layout.addLayout(
            measure_controls
        )

        self.measurement_label = QLabel()
        self.measurement_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        layout.addWidget(
            self.measurement_label
        )

        self.scene = QGraphicsScene()

        self.view = QGraphicsView(
            self.scene
        )
        self.view.setRenderHint(
            QPainter.Antialiasing,
            True
        )
        self.view.setDragMode(
            QGraphicsView.ScrollHandDrag
        )

        self.view.setMinimumHeight(220)
        self.view.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        self.station_animation = (
            StationAnimationWidget(
                self.configuration
            )
        )
        self.station_animation.setMinimumHeight(90)
        self.station_animation.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )

        self.trajectory_splitter = QSplitter(Qt.Vertical)
        self.trajectory_splitter.addWidget(self.view)
        self.trajectory_splitter.addWidget(self.station_animation)
        self.trajectory_splitter.setStretchFactor(0, 4)
        self.trajectory_splitter.setStretchFactor(1, 1)
        self.trajectory_splitter.setCollapsible(0, False)
        self.trajectory_splitter.setCollapsible(1, True)
        self.trajectory_splitter.setHandleWidth(8)
        self.trajectory_splitter.setSizes([720, 220])
        self.trajectory_splitter.setStyleSheet(
            "QSplitter::handle:vertical {"
            "background-color: #b8c8d4; height: 8px; "
            "margin-left: 4px; margin-right: 4px; border-radius: 3px;"
            "}"
            "QSplitter::handle:vertical:hover { background-color: #125b88; }"
        )
        self._station_animation_last_size = 220

        layout.addWidget(self.trajectory_splitter, 1)

        self.setLayout(
            layout
        )

    def _toggle_station_animation(self):
        visible = not self.station_animation.isVisible()
        sizes = self.trajectory_splitter.sizes()
        if visible:
            panel_size = max(90, int(self._station_animation_last_size))
            self.station_animation.show()
            available = max(
                310,
                sum(sizes) if sizes else self.trajectory_splitter.height()
            )
            self.trajectory_splitter.setSizes([
                max(220, available - panel_size),
                panel_size
            ])
        else:
            if len(sizes) == 2 and sizes[1] > 0:
                self._station_animation_last_size = sizes[1]
            self.station_animation.hide()
            self.trajectory_splitter.setSizes([max(1, sum(sizes)), 0])
        self.toggle_station_animation_button.setText(
            "Ukryj czasy wanien" if visible else "Pokaż czasy wanien"
        )

    def _measurement_slider_changed(self, lower, upper):
        self._update_measurement_label()
        self.draw()

    def _measurement_times(self):
        lower, upper = self.measure_slider.values()
        return (
            self._slider_value_to_time(lower),
            self._slider_value_to_time(upper)
        )

    def _format_mm_ss(self, seconds):
        seconds = max(0.0, float(seconds))
        minutes = int(seconds // 60)
        remaining = seconds - minutes * 60
        return f"{minutes:02d}:{remaining:04.1f}"

    def _update_measurement_label(self):
        time_a, time_b = self._measurement_times()
        difference = abs(time_b - time_a)
        self.measurement_label.setText(
            f"Punkt A: {time_a:.1f} s    |    "
            f"Punkt B: {time_b:.1f} s    |    "
            f"Różnica: {difference:.1f} s    |    "
            f"{self._format_mm_ss(difference)}"
        )

    def _reset_measurement_slider(self):
        self.measure_slider.setRange(0, self.SLIDER_MAX)
        self.measure_slider.setValues(
            int(round(self.SLIDER_MAX * 0.25)),
            int(round(self.SLIDER_MAX * 0.75))
        )
        self._update_measurement_label()

    def _draw_measurement_lines(self):
        if not hasattr(self, "measure_slider"):
            return
        time_a, time_b = self._measurement_times()
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        for label, time_value, color in [
            ("A", time_a, QColor(30, 110, 220)),
            ("B", time_b, QColor(180, 50, 180))
        ]:
            x = self._x(time_value)
            pen = QPen(color)
            pen.setWidth(2)
            pen.setStyle(Qt.DashLine)
            line = self.scene.addLine(
                x,
                self.margin_top,
                x,
                self.scene_height - self.margin_bottom,
                pen
            )
            line.setZValue(900)
            text = self.scene.addText(
                f"{label} {time_value:.1f}s",
                font
            )
            text.setDefaultTextColor(color)
            text.setPos(x + 4, self.margin_top + 20)
            text.setZValue(901)

    def update_result(
        self,
        result
    ):
        """
        Aktualizacja wyniku EventDriven.
        Ta metoda zostaje kompatybilna z istniejącym SimulationTab.
        """
        self.event_result = (
            result
        )

        self.result = (
            self._active_result()
        )

        self._after_result_update(
            reset_window=True
        )

    def update_program_result(
        self,
        result
    ):
        """
        Aktualizacja wyniku ProgramDriven.
        Wywoływana po kliknięciu 'Symuluj program PLC'.
        """
        self.program_result = (
            result
        )

        self.result = (
            self._active_result()
        )

        self._after_result_update(
            reset_window=False
        )

    def clear_program_result(
        self
    ):
        self.program_result = None

        self.result = (
            self._active_result()
        )

        self.draw()

    def _after_result_update(
        self,
        reset_window
    ):
        active_result = (
            self._active_result()
        )

        self.result = (
            active_result
        )

        if hasattr(
            self,
            "station_animation"
        ):
            self.station_animation.update_result(
                active_result
            )

        final_time = (
            self._final_time()
        )

        self.start_time.blockSignals(
            True
        )
        self.end_time.blockSignals(
            True
        )

        self.start_time.setMaximum(
            max(
                final_time,
                1.0
            )
        )
        self.end_time.setMaximum(
            max(
                final_time,
                1.0
            )
        )

        if reset_window or self.end_time.value() <= self.start_time.value():
            self.start_time.setValue(
                0.0
            )
            self.end_time.setValue(
                min(
                    final_time,
                    600.0
                )
            )
        else:
            self.end_time.setValue(
                min(
                    self.end_time.value(),
                    final_time
                )
            )

        self.start_time.blockSignals(
            False
        )
        self.end_time.blockSignals(
            False
        )

        self._set_current_time(
            self.start_time.value()
        )

    def _source_changed(
        self
    ):
        active_result = (
            self._active_result()
        )

        self.result = (
            active_result
        )

        if hasattr(
            self,
            "station_animation"
        ):
            self.station_animation.update_result(
                active_result
            )

        final_time = (
            self._final_time()
        )

        self.start_time.blockSignals(
            True
        )
        self.end_time.blockSignals(
            True
        )

        self.start_time.setMaximum(
            max(
                final_time,
                1.0
            )
        )

        self.end_time.setMaximum(
            max(
                final_time,
                1.0
            )
        )

        if (
            self.end_time.value()
            <=
            self.start_time.value()
            or
            self.end_time.value()
            >
            final_time
        ):
            self.start_time.setValue(
                0.0
            )

            self.end_time.setValue(
                min(
                    final_time,
                    600.0
                )
            )

        self.start_time.blockSignals(
            False
        )
        self.end_time.blockSignals(
            False
        )

        self._set_current_time(
            max(
                self.start_time.value(),
                min(
                    self.current_time,
                    self.end_time.value()
                )
            )
        )

    def _source_mode(
        self
    ):
        return (
            self.source_mode.currentData()
            or
            self.SOURCE_EVENT
        )

    def _active_result(
        self
    ):
        mode = (
            self._source_mode()
        )

        if mode == self.SOURCE_PROGRAM:
            return (
                self.program_result
                if self.program_result is not None
                else self.event_result
            )

        if mode == self.SOURCE_OVERLAY:
            return (
                self.event_result
                if self.event_result is not None
                else self.program_result
            )

        return (
            self.event_result
        )

    def _results_to_draw(
        self
    ):
        mode = (
            self._source_mode()
        )

        if mode == self.SOURCE_OVERLAY:
            results = []

            if self.event_result is not None:
                results.append(
                    (
                        "EventDriven",
                        self.event_result,
                        "event"
                    )
                )

            if self.program_result is not None:
                results.append(
                    (
                        "ProgramDriven",
                        self.program_result,
                        "program"
                    )
                )

            return results

        if mode == self.SOURCE_PROGRAM:
            if self.program_result is not None:
                return [
                    (
                        "ProgramDriven",
                        self.program_result,
                        "program"
                    )
                ]

            return []

        if self.event_result is not None:
            return [
                (
                    "EventDriven",
                    self.event_result,
                    "event"
                )
            ]

        return []

    def _window_changed(
        self
    ):
        if self._active_result() is None:
            return

        if (
            self.end_time.value()
            <=
            self.start_time.value()
        ):
            return

        if (
            self.current_time
            <
            self.start_time.value()
            or
            self.current_time
            >
            self.end_time.value()
        ):
            self.current_time = (
                self.start_time.value()
            )

        self._sync_time_controls()
        self._update_measurement_label()
        self.draw()

    def _final_time_for_result(
        self,
        result
    ):
        if result is None:
            return 0.0

        final_time = getattr(
            result,
            "final_time",
            0.0
        )

        if final_time > 0:
            return float(
                final_time
            )

        max_time = 0.0

        for segment in getattr(
            result,
            "timeline_segments",
            []
        ):
            max_time = max(
                max_time,
                float(
                    segment.end_time
                )
            )

        return max_time

    def _final_time(
        self
    ):
        if self._source_mode() == self.SOURCE_OVERLAY:
            return max(
                self._final_time_for_result(
                    self.event_result
                ),
                self._final_time_for_result(
                    self.program_result
                )
            )

        return (
            self._final_time_for_result(
                self._active_result()
            )
        )

    def _station_name_map(
        self
    ):
        result = {
            station.id:
                station.name
            for station
            in getattr(
                self.configuration,
                "stations",
                []
            )
        }
        result.setdefault(
            23,
            "Przeładunek dół"
        )
        result.setdefault(
            24,
            "Przeładunek góra"
        )
        return result

    def _active_station_ids(
        self
    ):
        return {
            station.id
            for station
            in getattr(
                self.configuration,
                "stations",
                []
            )
            if getattr(
                station,
                "enabled",
                True
            )
        }

    def _all_position_ids(
        self
    ):
        ids = set()

        for station in getattr(
            self.configuration,
            "stations",
            []
        ):
            ids.add(
                int(
                    station.id
                )
            )

        for _label, result, _source_kind in self._results_to_draw():
            for segment in getattr(
                result,
                "timeline_segments",
                []
            ):
                ids.add(
                    int(
                        round(
                            segment.start_position
                        )
                    )
                )

                ids.add(
                    int(
                        round(
                            segment.end_position
                        )
                    )
                )

            for task in getattr(
                result,
                "manipulator_tasks",
                []
            ):
                ids.add(
                    int(
                        task.source_station
                    )
                )

                ids.add(
                    int(
                        task.target_station
                    )
                )

        if not ids:
            return []

        return list(
            range(
                min(
                    ids
                ),
                max(
                    ids
                )
                +
                1
            )
        )

    def _manipulator_ids(
        self
    ):
        ids = set()

        for manipulator in getattr(
            self.configuration,
            "manipulators",
            []
        ):
            ids.add(
                manipulator.id
            )

        for _label, result, _source_kind in self._results_to_draw():
            for segment in getattr(
                result,
                "timeline_segments",
                []
            ):
                ids.add(
                    segment.manipulator_id
                )

        return sorted(
            ids
        )

    def _position_at(
        self,
        result,
        manipulator_id,
        time_value
    ):
        if result is None:
            return self._initial_manipulator_position(
                manipulator_id
            )

        candidate = None

        for segment in getattr(
            result,
            "timeline_segments",
            []
        ):
            if (
                segment.manipulator_id
                !=
                manipulator_id
            ):
                continue

            if (
                segment.start_time
                <=
                time_value
                <=
                segment.end_time
            ):
                if (
                    segment.end_time
                    <=
                    segment.start_time
                ):
                    return (
                        segment.end_position
                    )

                ratio = (
                    time_value
                    -
                    segment.start_time
                ) / (
                    segment.end_time
                    -
                    segment.start_time
                )

                return (
                    segment.start_position
                    +
                    (
                        segment.end_position
                        -
                        segment.start_position
                    )
                    *
                    ratio
                )

            if (
                segment.end_time
                <=
                time_value
            ):
                if (
                    candidate is None
                    or
                    segment.end_time
                    >
                    candidate[
                        0
                    ]
                ):
                    candidate = (
                        segment.end_time,
                        segment.end_position
                    )

        if candidate is not None:
            return (
                candidate[
                    1
                ]
            )

        return self._initial_manipulator_position(
            manipulator_id
        )

    def _initial_manipulator_position(
        self,
        manipulator_id
    ):
        for manipulator in getattr(
            self.configuration,
            "manipulators",
            []
        ):
            if (
                manipulator.id
                ==
                manipulator_id
            ):
                return (
                    manipulator.position
                )

        return 0.0

    def _x(
        self,
        time_value
    ):
        start = (
            self.start_time.value()
        )
        end = (
            self.end_time.value()
        )

        if (
            end
            <=
            start
        ):
            return (
                self.margin_left
            )

        usable_width = (
            self.scene_width
            -
            self.margin_left
            -
            self.margin_right
        )

        ratio = (
            time_value
            -
            start
        ) / (
            end
            -
            start
        )

        return (
            self.margin_left
            +
            usable_width
            *
            ratio
        )

    def _y(
        self,
        position
    ):
        positions = (
            self._all_position_ids()
        )

        if not positions:
            return (
                self.margin_top
            )

        minimum = min(
            positions
        )
        maximum = max(
            positions
        )

        if (
            maximum
            <=
            minimum
        ):
            return (
                self.margin_top
            )

        usable_height = (
            self.scene_height
            -
            self.margin_top
            -
            self.margin_bottom
        )

        ratio = (
            position
            -
            minimum
        ) / (
            maximum
            -
            minimum
        )

        return (
            self.margin_top
            +
            usable_height
            *
            (
                1.0
                -
                ratio
            )
        )

    def _clip_segment(
        self,
        segment,
        start_time,
        end_time
    ):
        left = max(
            float(
                segment.start_time
            ),
            start_time
        )

        right = min(
            float(
                segment.end_time
            ),
            end_time
        )

        if (
            right
            <
            left
        ):
            return None

        if (
            segment.end_time
            <=
            segment.start_time
        ):
            start_position = (
                segment.start_position
            )
            end_position = (
                segment.end_position
            )

        else:
            duration = (
                segment.end_time
                -
                segment.start_time
            )

            left_ratio = (
                left
                -
                segment.start_time
            ) / duration

            right_ratio = (
                right
                -
                segment.start_time
            ) / duration

            start_position = (
                segment.start_position
                +
                (
                    segment.end_position
                    -
                    segment.start_position
                )
                *
                left_ratio
            )

            end_position = (
                segment.start_position
                +
                (
                    segment.end_position
                    -
                    segment.start_position
                )
                *
                right_ratio
            )

        return (
            left,
            right,
            start_position,
            end_position
        )

    def _color_for_manipulator(
        self,
        manipulator_id
    ):
        return self.manipulator_colors.get(
            manipulator_id,
            QColor(
                80,
                80,
                80
            )
        )

    def _draw_background(
        self
    ):
        station_names = (
            self._station_name_map()
        )

        active_ids = (
            self._active_station_ids()
        )
        for _label, result, source_kind in self._results_to_draw():
            if source_kind != "program":
                continue
            for segment in getattr(result, "timeline_segments", []):
                for position in [
                    int(round(segment.start_position)),
                    int(round(segment.end_position))
                ]:
                    if position in [23, 24]:
                        active_ids.add(position)

        positions = (
            self._all_position_ids()
        )

        if not positions:
            return

        font = QFont()
        font.setPointSize(
            8
        )

        for position in positions:
            y = (
                self._y(
                    position
                )
            )

            if position not in active_ids:
                brush = QColor(
                    220,
                    220,
                    220,
                    70
                )

                self.scene.addRect(
                    self.margin_left,
                    y
                    -
                    9,
                    (
                        self.scene_width
                        -
                        self.margin_left
                        -
                        self.margin_right
                    ),
                    18,
                    QPen(
                        Qt.NoPen
                    ),
                    QBrush(
                        brush
                    )
                )

            line_pen = QPen(
                QColor(
                    210,
                    210,
                    210
                )
            )
            line_pen.setWidth(
                1
            )

            self.scene.addLine(
                self.margin_left,
                y,
                self.scene_width
                -
                self.margin_right,
                y,
                line_pen
            )

            label = (
                f"{position}"
            )

            name = station_names.get(
                position,
                ""
            )

            if name:
                label = (
                    f"{position}  {name}"
                )

            text_item = self.scene.addText(
                label,
                font
            )

            if position in active_ids:
                text_item.setDefaultTextColor(
                    QColor(
                        30,
                        30,
                        30
                    )
                )
            else:
                text_item.setDefaultTextColor(
                    QColor(
                        120,
                        120,
                        120
                    )
                )

            text_item.setPos(
                5,
                y
                -
                10
            )

        axis_pen = QPen(
            QColor(
                80,
                80,
                80
            )
        )
        axis_pen.setWidth(
            2
        )

        self.scene.addLine(
            self.margin_left,
            self.margin_top,
            self.margin_left,
            self.scene_height
            -
            self.margin_bottom,
            axis_pen
        )

        self.scene.addLine(
            self.margin_left,
            self.scene_height
            -
            self.margin_bottom,
            self.scene_width
            -
            self.margin_right,
            self.scene_height
            -
            self.margin_bottom,
            axis_pen
        )

    def _draw_time_axis(
        self
    ):
        start = (
            self.start_time.value()
        )

        end = (
            self.end_time.value()
        )

        if (
            end
            <=
            start
        ):
            return

        font = QFont()
        font.setPointSize(
            8
        )

        span = (
            end
            -
            start
        )

        if span <= 300:
            step = 30

        elif span <= 1200:
            step = 120

        elif span <= 3600:
            step = 300

        else:
            step = 600

        first_tick = (
            int(
                start
                //
                step
            )
            *
            step
        )

        tick = (
            first_tick
        )

        while (
            tick
            <=
            end
        ):
            if (
                tick
                >=
                start
            ):
                x = (
                    self._x(
                        tick
                    )
                )

                self.scene.addLine(
                    x,
                    self.scene_height
                    -
                    self.margin_bottom,
                    x,
                    self.scene_height
                    -
                    self.margin_bottom
                    +
                    6,
                    QPen(
                        QColor(
                            80,
                            80,
                            80
                        )
                    )
                )

                text_item = self.scene.addText(
                    f"{tick:.0f}",
                    font
                )

                text_item.setDefaultTextColor(
                    QColor(
                        80,
                        80,
                        80
                    )
                )

                text_item.setPos(
                    x
                    -
                    15,
                    self.scene_height
                    -
                    self.margin_bottom
                    +
                    8
                )

            tick += step

    def _draw_legend(
        self
    ):
        font = QFont()
        font.setPointSize(
            9
        )

        x = (
            self.margin_left
        )

        y = (
            8
        )

        for manipulator_id in self._manipulator_ids():
            color = (
                self._color_for_manipulator(
                    manipulator_id
                )
            )

            self.scene.addRect(
                x,
                y
                +
                5,
                14,
                8,
                QPen(
                    color
                ),
                QBrush(
                    color
                )
            )

            text = self.scene.addText(
                f"M{manipulator_id}",
                font
            )

            text.setDefaultTextColor(
                QColor(
                    30,
                    30,
                    30
                )
            )

            text.setPos(
                x
                +
                18,
                y
            )

            x += 60

        neutral = QColor(
            80,
            80,
            80
        )

        up_polygon = QPolygonF(
            [
                QPointF(
                    x
                    +
                    7,
                    y
                ),
                QPointF(
                    x,
                    y
                    +
                    15
                ),
                QPointF(
                    x
                    +
                    14,
                    y
                    +
                    15
                )
            ]
        )

        self.scene.addPolygon(
            up_polygon,
            QPen(
                neutral
            ),
            QBrush(
                neutral
            )
        )

        text = self.scene.addText(
            "podniesienie",
            font
        )

        text.setDefaultTextColor(
            neutral
        )

        text.setPos(
            x
            +
            20,
            y
        )

        x += 125

        down_polygon = QPolygonF(
            [
                QPointF(
                    x,
                    y
                ),
                QPointF(
                    x
                    +
                    14,
                    y
                ),
                QPointF(
                    x
                    +
                    7,
                    y
                    +
                    15
                )
            ]
        )

        self.scene.addPolygon(
            down_polygon,
            QPen(
                neutral
            ),
            QBrush(
                neutral
            )
        )

        text = self.scene.addText(
            "opuszczenie",
            font
        )

        text.setDefaultTextColor(
            neutral
        )

        text.setPos(
            x
            +
            20,
            y
        )

        x += 125

        if self._source_mode() == self.SOURCE_OVERLAY:
            event_pen = QPen(
                QColor(
                    40,
                    40,
                    40
                )
            )
            event_pen.setWidth(
                3
            )
            event_pen.setStyle(
                Qt.SolidLine
            )

            self.scene.addLine(
                x,
                y
                +
                8,
                x
                +
                30,
                y
                +
                8,
                event_pen
            )

            text = self.scene.addText(
                "EventDriven",
                font
            )
            text.setDefaultTextColor(
                QColor(
                    40,
                    40,
                    40
                )
            )
            text.setPos(
                x
                +
                35,
                y
            )

            x += 120

            program_pen = QPen(
                QColor(
                    40,
                    40,
                    40
                )
            )
            program_pen.setWidth(
                2
            )
            program_pen.setStyle(
                Qt.DashLine
            )

            self.scene.addLine(
                x,
                y
                +
                8,
                x
                +
                30,
                y
                +
                8,
                program_pen
            )

            text = self.scene.addText(
                "ProgramDriven",
                font
            )
            text.setDefaultTextColor(
                QColor(
                    40,
                    40,
                    40
                )
            )
            text.setPos(
                x
                +
                35,
                y
            )

    def _style_pen_for_segment(
        self,
        segment,
        source_kind
    ):
        color = (
            self._color_for_manipulator(
                segment.manipulator_id
            )
        )

        pen = QPen(
            color
        )

        segment_type = getattr(
            segment,
            "segment_type",
            ""
        )

        if source_kind == "program":
            pen.setWidth(
                2
            )
        else:
            pen.setWidth(
                3
            )

        if segment_type == "idle":
            pen.setStyle(
                Qt.DotLine
            )

        elif segment_type == "empty_move":
            pen.setStyle(
                Qt.DashLine
            )

        else:
            pen.setStyle(
                Qt.SolidLine
            )

        if (
            self._source_mode() == self.SOURCE_OVERLAY
            and
            source_kind == "program"
        ):
            pen.setWidth(
                2
            )
            pen.setStyle(
                Qt.DashLine
            )

        return pen

    def _draw_trajectory_segments(
        self
    ):
        start = (
            self.start_time.value()
        )

        shown_end = min(
            self.current_time,
            self.end_time.value()
        )

        for _label, result, source_kind in self._results_to_draw():

            for segment in getattr(
                result,
                "timeline_segments",
                []
            ):
                clipped = (
                    self._clip_segment(
                        segment,
                        start,
                        shown_end
                    )
                )

                if clipped is None:
                    continue

                left, right, start_position, end_position = (
                    clipped
                )

                pen = (
                    self._style_pen_for_segment(
                        segment,
                        source_kind
                    )
                )

                self.scene.addLine(
                    QLineF(
                        self._x(
                            left
                        ),
                        self._y(
                            start_position
                        ),
                        self._x(
                            right
                        ),
                        self._y(
                            end_position
                        )
                    ),
                    pen
                )

    def _draw_consult_waits(self):
        """Draw ProgramDriven consult blocking periods as red overlays."""
        if self._source_mode() not in [
            self.SOURCE_PROGRAM,
            self.SOURCE_OVERLAY
        ]:
            return
        result = self.program_result
        if result is None:
            return

        visible_start = float(self.start_time.value())
        visible_end = min(
            float(self.current_time),
            float(self.end_time.value())
        )
        if visible_end <= visible_start:
            return

        red = QColor(210, 35, 35)
        pen = QPen(red)
        pen.setWidth(6)
        pen.setStyle(Qt.SolidLine)
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)

        for wait in getattr(result, "consult_waits", []):
            left = max(visible_start, float(wait["start_time"]))
            right = min(visible_end, float(wait["end_time"]))
            if right <= left:
                continue

            y = self._y(float(wait["position"]))
            line = self.scene.addLine(
                QLineF(self._x(left), y, self._x(right), y),
                pen
            )
            line.setZValue(700)

            label = (
                f"C{int(wait['consult_no'])} → "
                f"{wait['label']}"
            )
            text = self.scene.addText(label, font)
            text.setDefaultTextColor(red)
            text.setPos(
                self._x((left + right) / 2.0) + 3,
                y - 20
            )
            text.setZValue(701)
            text.setToolTip(
                f"Consult C{int(wait['consult_no'])}: "
                f"M{int(wait['manipulator_id'])} "
                f"INDEX {int(wait['source_plc_index'])} czeka na "
                f"M{int(wait['target_manipulator_id'])} "
                f"INDEX {int(wait['target_plc_index'])}; "
                f"czas {float(wait['duration']):.1f} s"
            )

    def _draw_plc_index_labels(
        self
    ):
        if not hasattr(
            self,
            "show_plc_indexes"
        ):
            return

        if not self.show_plc_indexes.isChecked():
            return

        start_time = float(
            self.start_time.value()
        )

        visible_end_time = min(
            float(
                self.current_time
            ),
            float(
                self.end_time.value()
            )
        )

        if visible_end_time <= start_time:
            return

        font = QFont()
        font.setPointSize(
            8
        )
        font.setBold(
            True
        )

        drawn_keys = set()
        label_count_by_manipulator = {}

        valid_motion_types = {
            "loaded_move",
            "empty_move",
            "empty_parking",
            "return_move",
            "parking_move",
            "move"
        }

        for _label, result, source_kind in self._results_to_draw():

            if source_kind != "program":
                continue

            executions = list(
                getattr(
                    result,
                    "program_word_executions",
                    []
                )
            )

            segments = list(
                getattr(
                    result,
                    "timeline_segments",
                    []
                )
            )

            executions_by_manipulator = {}

            for execution in executions:

                manipulator_id = getattr(
                    execution,
                    "manipulator_id",
                    None
                )

                if manipulator_id is None:
                    continue

                try:
                    manipulator_id = int(
                        manipulator_id
                    )

                except Exception:
                    continue

                word_kind = str(
                    getattr(
                        execution,
                        "word_kind",
                        getattr(
                            execution,
                            "command_name",
                            ""
                        )
                    )
                ).strip().upper()

                #
                # Jeden logiczny indeks ma być przypisany do dojazdu
                # do stacji, dlatego używamy wyłącznie słowa STATION.
                #
                if word_kind not in [
                    "STATION",
                    "STACJA"
                ]:
                    continue

                executions_by_manipulator.setdefault(
                    manipulator_id,
                    []
                ).append(
                    execution
                )

            for manipulator_executions in (
                executions_by_manipulator.values()
            ):
                manipulator_executions.sort(
                    key=lambda item: (
                        float(
                            getattr(
                                item,
                                "start_time",
                                0.0
                            )
                        ),
                        int(
                            getattr(
                                item,
                                "plc_index",
                                getattr(
                                    item,
                                    "word_index",
                                    0
                                )
                            )
                        )
                    )
                )

            for segment in segments:

                try:
                    manipulator_id = int(
                        segment.manipulator_id
                    )

                    segment_start = float(
                        segment.start_time
                    )

                    segment_end = float(
                        segment.end_time
                    )

                    start_position = float(
                        segment.start_position
                    )

                    end_position = float(
                        segment.end_position
                    )

                except Exception:
                    continue

                if (
                    segment_end < start_time
                    or
                    segment_start > visible_end_time
                ):
                    continue

                #
                # Indeks pokazujemy tylko na rzeczywistym ruchu.
                #
                if (
                    abs(
                        end_position
                        -
                        start_position
                    )
                    <=
                    1e-6
                ):
                    continue

                segment_type = str(
                    getattr(
                        segment,
                        "segment_type",
                        ""
                    )
                ).strip().lower()

                #
                # Jeżeli typ segmentu jest znany, musi być ruchem.
                # Dla starszych wyników bez segment_type wystarcza
                # faktyczna zmiana pozycji.
                #
                if (
                    segment_type
                    and
                    segment_type
                    not in valid_motion_types
                    and
                    "move"
                    not in segment_type
                    and
                    "travel"
                    not in segment_type
                    and
                    "parking"
                    not in segment_type
                ):
                    continue

                manipulator_executions = (
                    executions_by_manipulator.get(
                        manipulator_id,
                        []
                    )
                )

                if not manipulator_executions:
                    continue

                #
                # Ruch do nowej stacji zaczyna się po wykonaniu słowa
                # STATION. Szukamy ostatniego STATION nie późniejszego
                # niż początek danego ruchu.
                #
                matched_execution = None

                for execution in manipulator_executions:

                    execution_start = float(
                        getattr(
                            execution,
                            "start_time",
                            0.0
                        )
                    )

                    if (
                        execution_start
                        <=
                        segment_start
                        +
                        0.5
                    ):
                        matched_execution = execution

                    else:
                        break

                #
                # Fallback dla symulatora, który zapisuje segment ruchu
                # nieco przed start_time wykonania słowa.
                #
                if matched_execution is None:

                    best_distance = None

                    for execution in manipulator_executions:

                        execution_start = float(
                            getattr(
                                execution,
                                "start_time",
                                0.0
                            )
                        )

                        distance = abs(
                            execution_start
                            -
                            segment_start
                        )

                        if (
                            best_distance is None
                            or
                            distance < best_distance
                        ):
                            best_distance = distance
                            matched_execution = execution

                if matched_execution is None:
                    continue

                index_value = None

                for attribute_name in [
                    "plc_index",
                    "program_index",
                    "word_index",
                    "logical_step_no",
                    "step_no",
                    "index"
                ]:
                    value = getattr(
                        matched_execution,
                        attribute_name,
                        None
                    )

                    if value is None:
                        continue

                    try:
                        index_value = int(
                            value
                        )
                        break

                    except Exception:
                        continue

                if index_value is None:
                    continue

                cycle_no = int(
                    getattr(
                        matched_execution,
                        "cycle_no",
                        0
                    )
                )

                draw_key = (
                    manipulator_id,
                    cycle_no,
                    index_value,
                    round(
                        segment_start,
                        3
                    ),
                    round(
                        segment_end,
                        3
                    )
                )

                if draw_key in drawn_keys:
                    continue

                drawn_keys.add(
                    draw_key
                )

                #
                # Etykieta jest umieszczana na 40% długości ruchu,
                # nie dokładnie na początku, gdzie zwykle są markery
                # pickup/drop i inne odcinki.
                #
                label_ratio = 0.40

                label_time = (
                    segment_start
                    +
                    (
                        segment_end
                        -
                        segment_start
                    )
                    *
                    label_ratio
                )

                label_position = (
                    start_position
                    +
                    (
                        end_position
                        -
                        start_position
                    )
                    *
                    label_ratio
                )

                label_number = (
                    label_count_by_manipulator.get(
                        manipulator_id,
                        0
                    )
                )

                label_count_by_manipulator[
                    manipulator_id
                ] = (
                    label_number
                    +
                    1
                )

                #
                # Kolejne napisy są przesuwane naprzemiennie nad i pod
                # linię, co ogranicza nakładanie sąsiednich indeksów.
                #
                if label_number % 2 == 0:
                    vertical_offset = -22
                else:
                    vertical_offset = 5

                color = (
                    self._color_for_manipulator(
                        manipulator_id
                    )
                )

                text_item = self.scene.addText(
                    str(
                        index_value
                    ),
                    font
                )

                text_item.setDefaultTextColor(
                    color
                )

                text_item.setZValue(
                    100
                )

                text_item.setPos(
                    self._x(
                        label_time
                    )
                    +
                    3,
                    self._y(
                        label_position
                    )
                    +
                    vertical_offset
                )

                text_item.setToolTip(
                    f"M{manipulator_id} "
                    f"C{cycle_no} "
                    f"INDEX PLC {index_value} | "
                    f"{start_position:.0f} -> "
                    f"{end_position:.0f}"
                )

    def _draw_pickup_drop_markers(
        self
    ):
        start = (
            self.start_time.value()
        )

        shown_end = min(
            self.current_time,
            self.end_time.value()
        )

        for (
            _label,
            result,
            source_kind
        ) in self._results_to_draw():

            for task in getattr(
                result,
                "manipulator_tasks",
                []
            ):

                pickup_time = float(
                    getattr(
                        task,
                        "start_time",
                        0.0
                    )
                )

                drop_time = float(
                    getattr(
                        task,
                        "end_time",
                        0.0
                    )
                )

                manipulator_id = int(
                    task.manipulator_id
                )

                source_station = int(
                    task.source_station
                )

                target_station = int(
                    task.target_station
                )

                if (
                    start
                    <=
                    pickup_time
                    <=
                    shown_end
                ):
                    self._draw_up_marker(
                        pickup_time,
                        source_station,
                        manipulator_id,
                        source_kind
                    )

                if (
                    start
                    <=
                    drop_time
                    <=
                    shown_end
                ):
                    self._draw_down_marker(
                        drop_time,
                        target_station,
                        manipulator_id,
                        source_kind
                    )

    def _draw_up_marker(
        self,
        time_value,
        position,
        manipulator_id,
        source_kind="event"
    ):
        x = (
            self._x(
                time_value
            )
        )

        y = (
            self._y(
                position
            )
        )

        color = (
            self._color_for_manipulator(
                manipulator_id
            )
        )

        size = 7

        if source_kind == "program":
            size = 5

        polygon = QPolygonF(
            [
                QPointF(
                    x,
                    y
                    -
                    size
                    -
                    1
                ),
                QPointF(
                    x
                    -
                    size,
                    y
                    +
                    size
                ),
                QPointF(
                    x
                    +
                    size,
                    y
                    +
                    size
                )
            ]
        )

        self.scene.addPolygon(
            polygon,
            QPen(
                color
            ),
            QBrush(
                color
            )
        )

    def _draw_down_marker(
        self,
        time_value,
        position,
        manipulator_id,
        source_kind="event"
    ):
        x = (
            self._x(
                time_value
            )
        )

        y = (
            self._y(
                position
            )
        )

        color = (
            self._color_for_manipulator(
                manipulator_id
            )
        )

        size = 7

        if source_kind == "program":
            size = 5

        polygon = QPolygonF(
            [
                QPointF(
                    x
                    -
                    size,
                    y
                    -
                    size
                ),
                QPointF(
                    x
                    +
                    size,
                    y
                    -
                    size
                ),
                QPointF(
                    x,
                    y
                    +
                    size
                    +
                    1
                )
            ]
        )

        self.scene.addPolygon(
            polygon,
            QPen(
                color
            ),
            QBrush(
                color
            )
        )
    def _draw_handoffs(
        self
    ):
        return
#         if (
#             self.program_result
#             is None
#         ):
#             return
# 
#         handoff_stations = {
#             8,
#             14,
#             19
#         }
# 
#         font = QFont()
#         font.setPointSize(
#             7
#         )
# 
#         for task in getattr(
#             self.program_result,
#             "manipulator_tasks",
#             []
#         ):
# 
#             station = int(
#                 task.target_station
#             )
# 
#             if (
#                 station
#                 not in handoff_stations
#             ):
#                 continue
# 
#             x = self._x(
#                 task.end_time
#             )
# 
#             y = self._y(
#                 station
#             )
# 
#             self.scene.addEllipse(
#                 x - 3,
#                 y - 3,
#                 6,
#                 6,
#                 QPen(
#                     QColor(
#                         180,
#                         0,
#                         0
#                     )
#                 ),
#                 QBrush(
#                     QColor(
#                         255,
#                         0,
#                         0
#                     )
#                 )
#             )
# 
#             txt = self.scene.addText(
#                 f"H{task.hanger_id}",
#                 font
#             )
# 
#             txt.setPos(
#                 x + 4,
#                 y - 4
#             )
    def _draw_parking_events(
        self
    ):
        if (
            self.program_result
            is None
        ):
            return

        program = (
            self.program_result
        )

        for segment in getattr(
            program,
            "timeline_segments",
            []
        ):

            if (
                getattr(
                    segment,
                    "segment_type",
                    ""
                )
                !=
                "empty_parking"
            ):
                continue

            left = float(
                segment.start_time
            )

            right = float(
                segment.end_time
            )

            if (
                right
                <
                self.start_time.value()
            ):
                continue

            if (
                left
                >
                self.end_time.value()
            ):
                continue

            pen = QPen(
                QColor(
                    255,
                    140,
                    0
                )
            )

            pen.setStyle(
                Qt.DotLine
            )

            pen.setWidth(
                3
            )

            self.scene.addLine(
                QLineF(
                    self._x(left),
                    self._y(
                        segment.start_position
                    ),
                    self._x(right),
                    self._y(
                        segment.end_position
                    )
                ),
                pen
            )
    def _draw_current_manipulator_positions(
        self
    ):
        font = QFont()
        font.setPointSize(
            9
        )
        font.setBold(
            True
        )

        mode = (
            self._source_mode()
        )

        for manipulator_id in self._manipulator_ids():

            if mode == self.SOURCE_OVERLAY:
                self._draw_current_position_marker(
                    manipulator_id,
                    self.event_result,
                    "event",
                    font
                )

                self._draw_current_position_marker(
                    manipulator_id,
                    self.program_result,
                    "program",
                    font
                )

            else:
                self._draw_current_position_marker(
                    manipulator_id,
                    self._active_result(),
                    mode,
                    font
                )

    def _draw_current_position_marker(
        self,
        manipulator_id,
        result,
        source_kind,
        font
    ):
        if result is None:
            return

        position = (
            self._position_at(
                result,
                manipulator_id,
                self.current_time
            )
        )

        x = (
            self._x(
                self.current_time
            )
        )

        y = (
            self._y(
                position
            )
        )

        color = (
            self._color_for_manipulator(
                manipulator_id
            )
        )

        if (
            source_kind == "program"
            and
            self._source_mode() == self.SOURCE_OVERLAY
        ):
            self.scene.addRect(
                x
                -
                6,
                y
                -
                6,
                12,
                12,
                QPen(
                    QColor(
                        20,
                        20,
                        20
                    )
                ),
                QBrush(
                    color
                )
            )

            suffix = "P"

        else:
            self.scene.addEllipse(
                x
                -
                7,
                y
                -
                7,
                14,
                14,
                QPen(
                    QColor(
                        20,
                        20,
                        20
                    )
                ),
                QBrush(
                    color
                )
            )

            suffix = "E"

        if self._source_mode() == self.SOURCE_OVERLAY:
            label = (
                f"M{manipulator_id}{suffix}"
            )
        else:
            label = (
                f"M{manipulator_id}"
            )

        text_item = self.scene.addText(
            label,
            font
        )

        text_item.setDefaultTextColor(
            color
        )

        text_item.setPos(
            x
            +
            8,
            y
            -
            12
        )
    def _draw_cycle_markers(
        self
    ):
        mode = (
            self._source_mode()
        )

        if (
            mode
            ==
            self.SOURCE_EVENT
        ):
            return

        result = (
            self.program_result
        )

        if result is None:
            return

        markers = getattr(
            result,
            "program_word_executions",
            []
        )

        if not markers:
            return

        cycle_starts = {}

        for word in markers:

            cycle_no = int(
                getattr(
                    word,
                    "cycle_no",
                    1
                )
            )

            start_time = float(
                word.start_time
            )

            if (
                cycle_no
                not in cycle_starts
            ):
                cycle_starts[
                    cycle_no
                ] = start_time

            else:
                cycle_starts[
                    cycle_no
                ] = min(
                    cycle_starts[
                        cycle_no
                    ],
                    start_time
                )

        font = QFont()
        font.setPointSize(
            8
        )

        for cycle_no in sorted(
            cycle_starts.keys()
        ):
            time_value = (
                cycle_starts[
                    cycle_no
                ]
            )

            if (
                time_value
                <
                self.start_time.value()
                or
                time_value
                >
                self.end_time.value()
            ):
                continue

            x = (
                self._x(
                    time_value
                )
            )

            pen = QPen(
                QColor(
                    150,
                    150,
                    150
                )
            )

            pen.setStyle(
                Qt.DashDotLine
            )

            self.scene.addLine(
                x,
                self.margin_top,
                x,
                self.scene_height
                -
                self.margin_bottom,
                pen
            )

            text = self.scene.addText(
                f"C{cycle_no}",
                font
            )

            text.setDefaultTextColor(
                QColor(
                    120,
                    120,
                    120
                )
            )

            text.setPos(
                x + 2,
                self.margin_top + 2
            )
    def _draw_current_time_line(
        self
    ):
        x = (
            self._x(
                self.current_time
            )
        )

        pen = QPen(
            QColor(
                40,
                40,
                40
            )
        )
        pen.setStyle(
            Qt.DashLine
        )
        pen.setWidth(
            1
        )

        self.scene.addLine(
            x,
            self.margin_top,
            x,
            self.scene_height
            -
            self.margin_bottom,
            pen
        )

        font = QFont()
        font.setPointSize(
            9
        )
        font.setBold(
            True
        )

        text = self.scene.addText(
            f"t = {self.current_time:.1f}s",
            font
        )

        text.setDefaultTextColor(
            QColor(
                40,
                40,
                40
            )
        )

        text.setPos(
            x
            +
            6,
            self.margin_top
        )

    def _time_to_slider_value(
        self,
        time_value
    ):
        start = (
            self.start_time.value()
        )

        end = (
            self.end_time.value()
        )

        if (
            end
            <=
            start
        ):
            return 0

        ratio = (
            time_value
            -
            start
        ) / (
            end
            -
            start
        )

        ratio = max(
            0.0,
            min(
                1.0,
                ratio
            )
        )

        return int(
            round(
                ratio
                *
                self.SLIDER_MAX
            )
        )

    def _slider_value_to_time(
        self,
        slider_value
    ):
        start = (
            self.start_time.value()
        )

        end = (
            self.end_time.value()
        )

        if (
            end
            <=
            start
        ):
            return start

        ratio = (
            slider_value
            /
            self.SLIDER_MAX
        )

        return (
            start
            +
            (
                end
                -
                start
            )
            *
            ratio
        )

    def _sync_time_controls(
        self
    ):
        self.time_slider.blockSignals(
            True
        )
        self.time_spin.blockSignals(
            True
        )

        self.time_slider.setValue(
            self._time_to_slider_value(
                self.current_time
            )
        )

        self.time_spin.setMinimum(
            self.start_time.value()
        )

        self.time_spin.setMaximum(
            self.end_time.value()
        )

        self.time_spin.setValue(
            self.current_time
        )

        self.time_slider.blockSignals(
            False
        )
        self.time_spin.blockSignals(
            False
        )

    def _set_current_time(
        self,
        time_value
    ):
        start = (
            self.start_time.value()
        )

        end = (
            self.end_time.value()
        )

        if (
            end
            <=
            start
        ):
            self.current_time = start

        else:
            self.current_time = max(
                start,
                min(
                    end,
                    float(
                        time_value
                    )
                )
            )

        self._sync_time_controls()
        self.draw()

    def _slider_changed(
        self,
        value
    ):
        if self._active_result() is None:
            return

        self._set_current_time(
            self._slider_value_to_time(
                value
            )
        )

    def _time_spin_changed(
        self,
        value
    ):
        if self._active_result() is None:
            return

        self._set_current_time(
            value
        )

    def draw(
        self
    ):
        self.scene.clear()

        self.scene.setSceneRect(
            0,
            0,
            self.scene_width,
            self.scene_height
        )

        if not self._results_to_draw():
            self.scene.addText(
                "Brak wyników dla wybranego źródła."
            )
            return

        self._draw_background()

        self._draw_time_axis()

        self._draw_legend()

        self._draw_trajectory_segments()

        self._draw_consult_waits()

        self._draw_plc_index_labels()

        self._draw_pickup_drop_markers()

        self._draw_cycle_markers()

        self._draw_parking_events()

        self._draw_handoffs()

        self._draw_current_time_line()
        self._draw_measurement_lines()

        self._draw_current_manipulator_positions()

        if hasattr(
            self,
            "station_animation"
        ):
            self.station_animation.update_time(
                self.current_time
            )
    def _build_program_cycle_windows(
        self
    ):
        self.program_cycle_windows = []

        result = self.program_result

        if result is None:
            return

        executions = getattr(
            result,
            "program_word_executions",
            []
        )

        if not executions:
            return

        cycle_starts = {}

        for word in executions:

            cycle_no = int(
                getattr(
                    word,
                    "cycle_no",
                    1
                )
            )

            start_time = float(
                word.start_time
            )

            if cycle_no not in cycle_starts:
                cycle_starts[
                    cycle_no
                ] = start_time

            else:
                cycle_starts[
                    cycle_no
                ] = min(
                    cycle_starts[
                        cycle_no
                    ],
                    start_time
                )

        ordered = sorted(
            cycle_starts.items()
        )

        for index in range(
            len(ordered)
        ):
            cycle_no, start_time = ordered[index]

            if (
                index
                <
                len(ordered)
                - 1
            ):
                end_time = ordered[
                    index + 1
                ][1]

            else:
                end_time = self._final_time()

            if end_time > start_time:
                self.program_cycle_windows.append(
                    (
                        cycle_no,
                        start_time,
                        end_time
                    )
                )
    def _set_cycle_window(
        self,
        index
    ):
        self._build_program_cycle_windows()

        if not self.program_cycle_windows:
            return

        index = max(
            0,
            min(
                index,
                len(
                    self.program_cycle_windows
                ) - 1
            )
        )

        self.program_cycle_index = index

        cycle_no, start_time, _ = (
            self.program_cycle_windows[index]
        )
        last_index = min(
            len(
                self.program_cycle_windows
            ) - 1,
            index
            +
            self._visible_cycle_count()
            -
            1
        )
        _, _, end_time = (
            self.program_cycle_windows[
                last_index
            ]
        )

        self.start_time.blockSignals(
            True
        )

        self.end_time.blockSignals(
            True
        )

        self.start_time.setValue(
            start_time
        )

        self.end_time.setValue(
            end_time
        )

        self.start_time.blockSignals(
            False
        )

        self.end_time.blockSignals(
            False
        )

        self.cycle_label.setText(
            f"Cykl: {cycle_no}"
        )
        

        self._set_current_time(
            start_time
        )
    def go_to_previous_cycle(
        self
    ):
        self._set_cycle_window(
            self.program_cycle_index - 1
        )
    def _cycle_span_changed(
        self
    ):
        self._set_cycle_window(
            self.program_cycle_index
        )
    def _visible_cycle_count(
        self
    ):
        return int(
            self.cycle_span.currentData()
            or
            1
        )

    def go_to_next_cycle(
        self
    ):
        self._set_cycle_window(
            self.program_cycle_index + 1
        )
    def toggle_animation(
        self
    ):
        if self._active_result() is None:
            return

        if self.animation_running:
            self.timer.stop()
            self.animation_running = False
            self.play_button.setText(
                "Play"
            )
            return

        self.animation_running = True
        self.play_button.setText(
            "Stop"
        )

        if (
            self.current_time
            <
            self.start_time.value()
            or
            self.current_time
            >=
            self.end_time.value()
        ):
            self.current_time = (
                self.start_time.value()
            )

        self._sync_time_controls()

        self.timer.start(
            100
        )

    def _animation_step(
        self
    ):
        if self._active_result() is None:
            return

        speed = float(
            self.speed.currentData()
        )

        next_time = (
            self.current_time
            +
            0.1
            *
            speed
        )

        if (
            next_time
            >=
            self.end_time.value()
        ):
            next_time = (
                self.end_time.value()
            )

            self.timer.stop()
            self.animation_running = False
            self.play_button.setText(
                "Play"
            )

        self._set_current_time(
            next_time
        )

    def reset_animation(
        self
    ):
        self.timer.stop()
        self.animation_running = False
        self.play_button.setText(
            "Play"
        )

        self._set_current_time(
            self.start_time.value()
        )

    def set_full_window(
        self
    ):
        final_time = (
            self._final_time()
        )

        if final_time <= 0:
            return

        self.start_time.blockSignals(
            True
        )
        self.end_time.blockSignals(
            True
        )

        self.start_time.setValue(
            0.0
        )

        self.end_time.setValue(
            final_time
        )

        self.start_time.blockSignals(
            False
        )
        self.end_time.blockSignals(
            False
        )

        self._set_current_time(
            0.0
        )

    def _average_lead_time(
        self
    ):
        result = (
            self._active_result()
        )

        if result is None:
            return 600.0

        summary = getattr(
            result,
            "lead_time_summary",
            None
        )

        if isinstance(
            summary,
            dict
        ):
            steady_average = (
                summary.get(
                    "steady_state_average_time",
                    0.0
                )
            )

            if steady_average > 0:
                return steady_average

            average_time = (
                summary.get(
                    "average_time",
                    0.0
                )
            )

            if average_time > 0:
                return average_time

        return 600.0

    def _steady_state_time(
        self
    ):
        result = (
            self._active_result()
        )

        if result is None:
            return 0.0

        steady_state = getattr(
            result,
            "steady_state",
            None
        )

        if isinstance(
            steady_state,
            dict
        ):
            value = steady_state.get(
                "steady_state_time",
                None
            )

            if value is not None:
                return float(
                    value
                )

        return 0.0

    def set_steady_state_window(
        self
    ):
        result = (
            self._active_result()
        )

        if result is None:
            return

        start_time = (
            self._steady_state_time()
        )

        average_lead_time = (
            self._average_lead_time()
        )

        final_time = (
            self._final_time()
        )

        if final_time <= 0:
            return

        end_time = min(
            final_time,
            start_time
            +
            average_lead_time
        )

        if (
            end_time
            <=
            start_time
        ):
            end_time = min(
                final_time,
                start_time
                +
                600.0
            )

        self.start_time.blockSignals(
            True
        )
        self.end_time.blockSignals(
            True
        )

        self.start_time.setValue(
            start_time
        )

        self.end_time.setValue(
            end_time
        )

        self.start_time.blockSignals(
            False
        )
        self.end_time.blockSignals(
            False
        )

        self._set_current_time(
            start_time
        )