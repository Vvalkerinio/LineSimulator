from src.model.station_numbering import display_station_id
from math import isinf

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QScrollArea,
    QFrame
)

from PySide6.QtCore import (
    Qt
)


class StationAnimationWidget(QWidget):

    def __init__(
        self,
        configuration
    ):
        super().__init__()

        self.configuration = configuration
        self.result = None
        self.current_time = 0.0

        self.station_cards = {}
        self.station_labels = {}
        self.hanger_labels = {}
        self.time_labels = {}

        self.intervals = []

        self._build_ui()

    def _build_ui(
        self
    ):
        main_layout = QVBoxLayout()

        header = QHBoxLayout()

        self.title = QLabel(
            "Stan stanowisk w czasie"
        )
        self.title.setStyleSheet(
            "font-weight: bold;"
        )
        header.addWidget(
            self.title
        )

        self.time_label = QLabel(
            "t = 0.0 s"
        )
        self.time_label.setAlignment(
            Qt.AlignRight
        )
        header.addWidget(
            self.time_label
        )

        main_layout.addLayout(
            header
        )

        legend = QHBoxLayout()

        legend.addWidget(
            self._legend_item(
                "Wolne",
                "#e5e5e5"
            )
        )

        legend.addWidget(
            self._legend_item(
                "Poniżej MIN",
                "#c9e8ff"
            )
        )

        legend.addWidget(
            self._legend_item(
                "W normie",
                "#b7f0b1"
            )
        )

        legend.addWidget(
            self._legend_item(
                "Blisko MAX",
                "#fff0a6"
            )
        )

        legend.addWidget(
            self._legend_item(
                "Po MAX",
                "#ff9c9c"
            )
        )

        legend.addStretch()

        main_layout.addLayout(
            legend
        )

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(
            True
        )

        self.content = QWidget()

        self.grid = QGridLayout()
        self.grid.setSpacing(
            6
        )

        self.content.setLayout(
            self.grid
        )

        self.scroll.setWidget(
            self.content
        )

        main_layout.addWidget(
            self.scroll
        )

        self.setLayout(
            main_layout
        )

        self.setMaximumHeight(
            310
        )

    def _legend_item(
        self,
        text,
        color
    ):
        widget = QWidget()

        layout = QHBoxLayout()
        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        box = QLabel()
        box.setFixedSize(
            18,
            14
        )
        box.setStyleSheet(
            f"background-color: {color}; "
            f"border: 1px solid #777;"
        )

        label = QLabel(
            text
        )

        layout.addWidget(
            box
        )

        layout.addWidget(
            label
        )

        widget.setLayout(
            layout
        )

        return widget

    def update_result(
        self,
        result
    ):
        self.result = result

        self.intervals = (
            self._build_station_intervals()
        )

        self._rebuild_cards()

        self.update_time(
            self.current_time
        )

    def update_time(
        self,
        current_time
    ):
        self.current_time = float(
            current_time
        )

        self.time_label.setText(
            f"t = {self.current_time:.1f} s"
        )

        occupancy = (
            self._occupancy_at(
                self.current_time
            )
        )

        for station_id in self.station_cards:
            info = occupancy.get(
                station_id
            )

            self._update_card(
                station_id,
                info
            )

    def _station_map(
        self
    ):
        return {
            station.id:
                station
            for station
            in getattr(
                self.configuration,
                "stations",
                []
            )
        }

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

        if self.result is not None:

            for segment in getattr(
                self.result,
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
                self.result,
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

    def _event_name(
        self,
        event
    ):
        event_type = getattr(
            event,
            "event_type",
            None
        )

        name = getattr(
            event_type,
            "name",
            None
        )

        if name is not None:
            return name

        return str(
            event_type
        )

    def _build_exit_times_from_loaded_moves(
        self
    ):
        exit_times = {}

        if self.result is None:
            return exit_times

        for segment in getattr(
            self.result,
            "timeline_segments",
            []
        ):
            segment_type = getattr(
                segment,
                "segment_type",
                ""
            )

            if (
                segment_type
                !=
                "loaded_move"
            ):
                continue

            hanger_id = getattr(
                segment,
                "hanger_id",
                None
            )

            if hanger_id is None:
                continue

            station_id = int(
                round(
                    segment.start_position
                )
            )

            pickup_time = getattr(
                segment,
                "pickup_time",
                None
            )

            if pickup_time is None:
                pickup_time = (
                    segment.start_time
                )

            key = (
                hanger_id,
                station_id
            )

            current = exit_times.get(
                key
            )

            if (
                current is None
                or
                pickup_time
                <
                current
            ):
                exit_times[
                    key
                ] = pickup_time

        return exit_times

    def _build_exit_times_from_hanger_exit(
        self
    ):
        exit_times = {}

        if self.result is None:
            return exit_times

        for event in getattr(
            self.result,
            "events",
            []
        ):
            name = (
                self._event_name(
                    event
                )
            )

            if (
                name
                !=
                "HANGER_EXIT"
            ):
                continue

            station_id = getattr(
                event,
                "source_station",
                None
            )

            if station_id is None:
                station_id = getattr(
                    event,
                    "target_station",
                    None
                )

            if station_id is None:
                continue

            exit_times[
                (
                    event.hanger_id,
                    station_id
                )
            ] = event.time

        return exit_times

    def _build_station_intervals(
        self
    ):
        intervals = []

        if self.result is None:
            return intervals

        station_entry_times = getattr(
            self.result,
            "station_entry_times",
            {}
        )

        loaded_move_exit_times = (
            self._build_exit_times_from_loaded_moves()
        )

        hanger_exit_times = (
            self._build_exit_times_from_hanger_exit()
        )

        if station_entry_times:
            for key, start_time in station_entry_times.items():
                hanger_id, station_id = key

                end_time = (
                    loaded_move_exit_times.get(
                        (
                            hanger_id,
                            station_id
                        )
                    )
                )

                if end_time is None:
                    end_time = (
                        hanger_exit_times.get(
                            (
                                hanger_id,
                                station_id
                            ),
                            float(
                                "inf"
                            )
                        )
                    )

                intervals.append(
                    {
                        "hanger_id":
                            hanger_id,

                        "station_id":
                            station_id,

                        "start_time":
                            start_time,

                        "end_time":
                            end_time,

                        "source":
                            "station_entry_times"
                    }
                )

            intervals.sort(
                key=lambda item:
                    (
                        item[
                            "station_id"
                        ],
                        item[
                            "start_time"
                        ]
                    )
            )

            return intervals

        #
        # Fallback, jeśli result.station_entry_times jeszcze nie istnieje.
        #
        for record in getattr(
            self.result,
            "process_compliance",
            []
        ):
            intervals.append(
                {
                    "hanger_id":
                        record.hanger_id,

                    "station_id":
                        record.station_id,

                    "start_time":
                        record.entry_time,

                    "end_time":
                        record.exit_time,

                    "source":
                        "process_compliance"
                }
            )

        intervals.sort(
            key=lambda item:
                (
                    item[
                        "station_id"
                    ],
                    item[
                        "start_time"
                    ]
                )
        )

        return intervals

    def _occupancy_at(
        self,
        current_time
    ):
        occupancy = {}

        for interval in self.intervals:
            start_time = (
                interval[
                    "start_time"
                ]
            )

            end_time = (
                interval[
                    "end_time"
                ]
            )

            if (
                start_time
                <= current_time
                and
                (
                    isinf(
                        end_time
                    )
                    or
                    current_time
                    <
                    end_time
                )
            ):
                station_id = (
                    interval[
                        "station_id"
                    ]
                )

                previous = occupancy.get(
                    station_id
                )

                if (
                    previous is None
                    or
                    interval[
                        "start_time"
                    ]
                    >
                    previous[
                        "start_time"
                    ]
                ):
                    occupancy[
                        station_id
                    ] = {
                        **interval,
                        "elapsed":
                            current_time
                            -
                            start_time
                    }

        return occupancy

    def _rebuild_cards(
        self
    ):
        while self.grid.count():
            item = (
                self.grid.takeAt(
                    0
                )
            )

            widget = (
                item.widget()
            )

            if widget is not None:
                widget.deleteLater()

        self.station_cards.clear()
        self.station_labels.clear()
        self.hanger_labels.clear()
        self.time_labels.clear()

        positions = (
            self._all_position_ids()
        )

        columns = 6

        for index, station_id in enumerate(
            positions
        ):
            row = (
                index
                //
                columns
            )

            column = (
                index
                %
                columns
            )

            card = (
                self._create_station_card(
                    station_id
                )
            )

            self.grid.addWidget(
                card,
                row,
                column
            )

    def _create_station_card(
        self,
        station_id
    ):
        station_map = (
            self._station_map()
        )

        station = station_map.get(
            station_id
        )

        active_ids = (
            self._active_station_ids()
        )

        card = QFrame()
        card.setFrameShape(
            QFrame.StyledPanel
        )

        card.setMinimumWidth(
            175
        )

        card.setMinimumHeight(
            108
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(
            6,
            4,
            6,
            4
        )

        name = ""

        if station is not None:
            name = getattr(
                station,
                "name",
                ""
            )

        station_label = QLabel(
            f"ST{display_station_id(station_id):02d}  {name}"
        )

        station_label.setStyleSheet(
            "font-weight: bold;"
        )

        hanger_label = QLabel(
            "---"
        )

        hanger_label.setAlignment(
            Qt.AlignCenter
        )

        hanger_label.setStyleSheet(
            "font-size: 14px; font-weight: bold;"
        )

        time_label = QLabel(
            ""
        )

        time_label.setAlignment(
            Qt.AlignCenter
        )

        time_label.setWordWrap(
            True
        )

        layout.addWidget(
            station_label
        )

        layout.addWidget(
            hanger_label
        )

        layout.addWidget(
            time_label
        )

        card.setLayout(
            layout
        )

        self.station_cards[
            station_id
        ] = card

        self.station_labels[
            station_id
        ] = station_label

        self.hanger_labels[
            station_id
        ] = hanger_label

        self.time_labels[
            station_id
        ] = time_label

        if station_id not in active_ids:
            self._apply_card_style(
                station_id,
                "#f0f0f0",
                "#999999",
                inactive=True
            )
        else:
            self._apply_card_style(
                station_id,
                "#e5e5e5",
                "#777777"
            )

        return card

    def _station_max_time(
        self,
        station_id
    ):
        station = (
            self._station_map()
            .get(
                station_id
            )
        )

        if station is None:
            return None

        return getattr(
            station,
            "max_process_time",
            None
        )

    def _station_min_time(
        self,
        station_id
    ):
        station = (
            self._station_map()
            .get(
                station_id
            )
        )

        if station is None:
            return None

        return getattr(
            station,
            "min_process_time",
            None
        )

    def _time_text(
        self,
        elapsed,
        min_time,
        max_time
    ):
        first_line = (
            f"{elapsed:.0f} s"
        )

        if (
            min_time is not None
            and
            max_time is not None
        ):
            return (
                f"{first_line}\n"
                f"MIN {min_time:.0f} | MAX {max_time:.0f}"
            )

        if min_time is not None:
            return (
                f"{first_line}\n"
                f"MIN {min_time:.0f}"
            )

        if max_time is not None:
            return (
                f"{first_line}\n"
                f"MAX {max_time:.0f}"
            )

        return first_line

    def _update_card(
        self,
        station_id,
        info
    ):
        active_ids = (
            self._active_station_ids()
        )

        if info is None:
            self.hanger_labels[
                station_id
            ].setText(
                "---"
            )

            self.time_labels[
                station_id
            ].setText(
                ""
            )

            if station_id not in active_ids:
                self._apply_card_style(
                    station_id,
                    "#f0f0f0",
                    "#999999",
                    inactive=True
                )
            else:
                self._apply_card_style(
                    station_id,
                    "#e5e5e5",
                    "#777777"
                )

            return

        hanger_id = (
            info[
                "hanger_id"
            ]
        )

        elapsed = (
            info[
                "elapsed"
            ]
        )

        max_time = (
            self._station_max_time(
                station_id
            )
        )

        min_time = (
            self._station_min_time(
                station_id
            )
        )

        self.hanger_labels[
            station_id
        ].setText(
            f"H{hanger_id}"
        )

        self.time_labels[
            station_id
        ].setText(
            self._time_text(
                elapsed,
                min_time,
                max_time
            )
        )

        if (
            max_time is not None
            and
            max_time > 0
            and
            elapsed > max_time
        ):
            self._apply_card_style(
                station_id,
                "#ff9c9c",
                "#a00000"
            )

            self.time_labels[
                station_id
            ].setStyleSheet(
                "font-weight: bold; color: #a00000;"
            )

            return

        if (
            max_time is not None
            and
            max_time > 0
            and
            elapsed >= 0.8 * max_time
        ):
            self._apply_card_style(
                station_id,
                "#fff0a6",
                "#9a7a00"
            )

            self.time_labels[
                station_id
            ].setStyleSheet(
                "font-weight: bold; color: #7a5f00;"
            )

            return

        if (
            min_time is not None
            and
            elapsed < min_time
        ):
            self._apply_card_style(
                station_id,
                "#c9e8ff",
                "#0060a8"
            )

            self.time_labels[
                station_id
            ].setStyleSheet(
                "font-weight: bold; color: #00558f;"
            )

            return

        self._apply_card_style(
            station_id,
            "#b7f0b1",
            "#207a20"
        )

        self.time_labels[
            station_id
        ].setStyleSheet(
            "font-weight: bold; color: #206020;"
        )

    def _apply_card_style(
        self,
        station_id,
        background,
        border,
        inactive=False
    ):
        card = (
            self.station_cards[
                station_id
            ]
        )

        border_style = (
            "dashed"
            if inactive
            else "solid"
        )

        card.setStyleSheet(
            f"QFrame {{ "
            f"background-color: {background}; "
            f"border: 2px {border_style} {border}; "
            f"border-radius: 6px; "
            f"}}"
        )

        self.time_labels[
            station_id
        ].setStyleSheet(
            "font-weight: normal; color: #333333;"
        )