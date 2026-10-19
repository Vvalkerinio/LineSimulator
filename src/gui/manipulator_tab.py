from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
    QCheckBox,
    QDoubleSpinBox,
    QSpinBox,
    QMessageBox
)

from PySide6.QtCore import (
    Qt
)

from src.model.station_numbering import (
    display_station_id,
    internal_station_id
)


class ManipulatorsTab(QWidget):

    HEADERS = [
        "ID",
        "Pozycja startowa [ST]",
        "Podnoszenie [s]",
        "Opuszczanie [s]",
        "Czas / pozycję [s]",
        "Ulubiony parking [ST]",
        "Strefa od [ST]",
        "Strefa do [ST]"
    ]

    def __init__(
        self,
        configuration
    ):
        super().__init__()

        self.configuration = (
            configuration
        )

        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(
            len(
                self.HEADERS
            )
        )
        self.table.setHorizontalHeaderLabels(
            self.HEADERS
        )

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        layout.addWidget(
            self.table
        )

        self.apply_button = QPushButton(
            "Zastosuj zmiany manipulatorów"
        )
        self.apply_button.clicked.connect(
            self.apply_changes
        )

        layout.addWidget(
            self.apply_button
        )

        self.setLayout(
            layout
        )

        self.refresh()

    def _set_readonly_item(
        self,
        row,
        column,
        value
    ):
        item = QTableWidgetItem(
            str(
                value
            )
        )
        item.setFlags(
            item.flags()
            & ~Qt.ItemIsEditable
        )
        self.table.setItem(
            row,
            column,
            item
        )
    def save_changes(
    self
    ):
        self.apply_changes()
    def _create_int_spinbox(
        self,
        value,
        minimum=1,
        maximum=999
    ):
        spinbox = QSpinBox()
        spinbox.setMinimum(
            minimum
        )
        spinbox.setMaximum(
            maximum
        )
        spinbox.setValue(
            int(
                value
            )
        )
        return spinbox

    def _create_float_spinbox(
        self,
        value,
        minimum=0.0,
        maximum=99999.0,
        decimals=2
    ):
        spinbox = QDoubleSpinBox()
        spinbox.setMinimum(
            minimum
        )
        spinbox.setMaximum(
            maximum
        )
        spinbox.setDecimals(
            decimals
        )
        spinbox.setValue(
            float(
                value
            )
        )
        return spinbox

    def _create_checkbox(
        self,
        checked
    ):
        checkbox = QCheckBox()
        checkbox.setChecked(
            bool(
                checked
            )
        )
        checkbox.setStyleSheet(
            "margin-left: 20px;"
        )
        return checkbox

    def refresh(
        self
    ):
        manipulators = (
            self.configuration.manipulators
        )

        self.table.setRowCount(
            len(
                manipulators
            )
        )

        for row, manipulator in enumerate(
            manipulators
        ):
            self._set_readonly_item(
                row,
                0,
                manipulator.id
            )

            self.table.setCellWidget(
                row,
                1,
                self._create_int_spinbox(
                    display_station_id(getattr(
                        manipulator,
                        "position",
                        1
                    )),
                    2,
                    23
                )
            )

            self.table.setCellWidget(
                row,
                2,
                self._create_float_spinbox(
                    getattr(
                        manipulator,
                        "lift_time",
                        3.0
                    ),
                    0.0,
                    3600.0
                )
            )

            self.table.setCellWidget(
                row,
                3,
                self._create_float_spinbox(
                    getattr(
                        manipulator,
                        "drop_time",
                        3.0
                    ),
                    0.0,
                    3600.0
                )
            )

            self.table.setCellWidget(
                row,
                4,
                self._create_float_spinbox(
                    getattr(
                        manipulator,
                        "travel_time_per_position",
                        2.0
                    ),
                    0.0,
                    3600.0
                )
            )

            self.table.setCellWidget(
                row,
                5,
                self._create_int_spinbox(
                    display_station_id(getattr(
                        manipulator,
                        "preferred_parking_position",
                        manipulator.position
                    )),
                    2,
                    23
                )
            )

            self.table.setCellWidget(
                row,
                6,
                self._create_int_spinbox(
                    display_station_id(getattr(
                        manipulator,
                        "work_zone_start",
                        1
                    )),
                    2,
                    23
                )
            )

            self.table.setCellWidget(
                row,
                7,
                self._create_int_spinbox(
                    display_station_id(getattr(
                        manipulator,
                        "work_zone_end",
                        22
                    )),
                    2,
                    23
                )
            )

    def _widget_value(
        self,
        row,
        column
    ):
        widget = (
            self.table.cellWidget(
                row,
                column
            )
        )

        if isinstance(
            widget,
            QCheckBox
        ):
            return (
                widget.isChecked()
            )

        if isinstance(
            widget,
            QSpinBox
        ):
            return (
                widget.value()
            )

        if isinstance(
            widget,
            QDoubleSpinBox
        ):
            return (
                widget.value()
            )

        return None

    def apply_changes(
        self
    ):
        proposed = []
        for row, manipulator in enumerate(
            self.configuration.manipulators
        ):
            position = internal_station_id(
                self._widget_value(row, 1)
            )
            parking = internal_station_id(
                self._widget_value(row, 5)
            )
            zone_start = internal_station_id(
                self._widget_value(row, 6)
            )
            zone_end = internal_station_id(
                self._widget_value(row, 7)
            )
            if zone_end < zone_start:
                zone_end = zone_start
            if not zone_start <= position <= zone_end:
                QMessageBox.warning(
                    self,
                    "Nieprawidłowa pozycja startowa",
                    f"M{manipulator.id}: pozycja startowa ST"
                    f"{display_station_id(position)} musi należeć do strefy "
                    f"ST{display_station_id(zone_start)}.."
                    f"ST{display_station_id(zone_end)}."
                )
                return
            proposed.append({
                "manipulator": manipulator,
                "position": position,
                "lift_time": float(self._widget_value(row, 2)),
                "drop_time": float(self._widget_value(row, 3)),
                "travel_time": float(self._widget_value(row, 4)),
                "parking": parking,
                "zone_start": zone_start,
                "zone_end": zone_end,
            })

        minimum_spacing = float(getattr(
            self.configuration,
            "minimum_manipulator_spacing",
            0.0
        ))
        ordered = sorted(proposed, key=lambda item: item["manipulator"].id)
        for left, right in zip(ordered, ordered[1:]):
            distance = right["position"] - left["position"]
            if distance < minimum_spacing:
                QMessageBox.warning(
                    self,
                    "Kolizja pozycji startowych",
                    f"M{left['manipulator'].id} na ST"
                    f"{display_station_id(left['position'])} i M"
                    f"{right['manipulator'].id} na ST"
                    f"{display_station_id(right['position'])} mają odstęp "
                    f"{distance:.1f}, wymagany: {minimum_spacing:.1f}."
                )
                return

        for item in proposed:
            manipulator = item["manipulator"]
            manipulator.position = item["position"]
            manipulator.lift_time = item["lift_time"]
            manipulator.drop_time = item["drop_time"]
            manipulator.travel_time_per_position = item["travel_time"]
            manipulator.preferred_parking_position = item["parking"]
            manipulator.work_zone_start = item["zone_start"]
            manipulator.work_zone_end = item["zone_end"]

        self.refresh()

        print(
            "Manipulator settings updated"
        )

        for manipulator in self.configuration.manipulators:
            print(
                f"M{manipulator.id} "
                f"pos={manipulator.position} "
                f"zone={manipulator.work_zone_start}"
                f"-{manipulator.work_zone_end}"
            )