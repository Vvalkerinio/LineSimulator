from src.model.station_numbering import display_station_id
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QCheckBox, QMessageBox
)

from src.gui.station_table_model import StationTableModel
from src.gui.shared_bath_settings_widget import SharedBathSettingsWidget
from src.core.shared_bath_group_builder import SharedBathGroupBuilder
from src.core.process_limit_classifier import validate_station_process_limits


class ProcessTab(QWidget):
    COLUMN_ID = 0
    COLUMN_NAME = 1
    COLUMN_ENABLED = 2
    COLUMN_PROCESS_BATH = 3
    COLUMN_POSSIBLE_MIN = 4
    COLUMN_MIN_TIME = 5
    COLUMN_MAX_TIME = 6
    COLUMN_POSSIBLE_MAX = 7
    COLUMN_DRIP_TIME = 8
    COLUMN_SHARED_BATH = 9

    def __init__(self, configuration):
        super().__init__()
        self.configuration = configuration
        self.model = StationTableModel(configuration.stations)
        layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nazwa", "Aktywne", "Wanna procesowa",
            "Possible Min [s]", "Min [s]", "Max [s]",
            "Possible Max [s]", "Czas ocieku [s]", "Shared Bath"
        ])
        self.table.setRowCount(self.model.row_count())
        self._load_data()
        layout.addWidget(self.table)
        self.shared_bath_settings_widget = SharedBathSettingsWidget()
        self.shared_bath_settings_widget.load_from_configuration(configuration)
        layout.addWidget(self.shared_bath_settings_widget)
        self.save_button = QPushButton("Zastosuj zmiany")
        self.save_button.clicked.connect(self.save_changes)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

    @staticmethod
    def _number(item):
        return float(item.text().strip().replace(",", "."))

    def _load_data(self):
        for row in range(self.model.row_count()):
            station = self.model.station(row)
            self.table.setItem(row, self.COLUMN_ID, QTableWidgetItem(str(display_station_id(station.id))))
            self.table.setItem(row, self.COLUMN_NAME, QTableWidgetItem(station.name))
            enabled = QCheckBox()
            enabled.setChecked(station.enabled)
            enabled.setLayoutDirection(Qt.RightToLeft)
            self.table.setCellWidget(row, self.COLUMN_ENABLED, enabled)
            process_bath = QCheckBox()
            process_bath.setChecked(bool(getattr(station, "is_process_bath", True)))
            process_bath.setToolTip(
                "Odznacz dla załadunku, rozładunku, transferu i legalnego parkingu."
            )
            self.table.setCellWidget(row, self.COLUMN_PROCESS_BATH, process_bath)
            values = {
                self.COLUMN_POSSIBLE_MIN: getattr(
                    station, "possible_min_process_time", station.min_process_time
                ),
                self.COLUMN_MIN_TIME: station.min_process_time,
                self.COLUMN_MAX_TIME: station.max_process_time,
                self.COLUMN_POSSIBLE_MAX: getattr(
                    station, "possible_max_process_time", station.max_process_time
                ),
                self.COLUMN_DRIP_TIME: getattr(station, "drip_time", 0.0),
            }
            for column, value in values.items():
                item = QTableWidgetItem(str(float(value)))
                if column in (self.COLUMN_POSSIBLE_MIN, self.COLUMN_POSSIBLE_MAX):
                    item.setToolTip(
                        "Twarda granica dopuszczalna dla optymalizacji. "
                        "Wyjście poza nią jest PROCESS_VIOLATION."
                    )
                self.table.setItem(row, column, item)
            shared = getattr(station, "shared_bath_group", None)
            self.table.setItem(
                row, self.COLUMN_SHARED_BATH,
                QTableWidgetItem("" if shared is None else str(shared))
            )

    def _row_values(self, row):
        required = [
            self.COLUMN_NAME, self.COLUMN_POSSIBLE_MIN, self.COLUMN_MIN_TIME,
            self.COLUMN_MAX_TIME, self.COLUMN_POSSIBLE_MAX,
            self.COLUMN_DRIP_TIME, self.COLUMN_SHARED_BATH
        ]
        items = {column: self.table.item(row, column) for column in required}
        if any(item is None for item in items.values()):
            raise ValueError(f"Wiersz {row + 1}: brak wymaganej wartości")
        possible_min = self._number(items[self.COLUMN_POSSIBLE_MIN])
        nominal_min = self._number(items[self.COLUMN_MIN_TIME])
        nominal_max = self._number(items[self.COLUMN_MAX_TIME])
        possible_max = self._number(items[self.COLUMN_POSSIBLE_MAX])
        if not (0.0 <= possible_min <= nominal_min <= nominal_max <= possible_max):
            raise ValueError(
                f"Wiersz {row + 1}: wymagane 0 <= Possible Min <= Min <= Max <= Possible Max; "
                f"otrzymano {possible_min}, {nominal_min}, {nominal_max}, {possible_max}"
            )
        return {
            "name": items[self.COLUMN_NAME].text(),
            "possible_min": possible_min,
            "min": nominal_min,
            "max": nominal_max,
            "possible_max": possible_max,
            "drip": max(0.0, self._number(items[self.COLUMN_DRIP_TIME])),
            "shared": items[self.COLUMN_SHARED_BATH].text().strip(),
        }

    def save_changes(self):
        try:
            rows = [self._row_values(row) for row in range(self.model.row_count())]
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self, "Nieprawidłowe granice procesu", str(exc))
            return False

        for row, values in enumerate(rows):
            enabled_widget = self.table.cellWidget(row, self.COLUMN_ENABLED)
            process_widget = self.table.cellWidget(row, self.COLUMN_PROCESS_BATH)
            shared = None if values["shared"].lower() in ("", "none") else values["shared"]
            self.model.update_station(
                row=row,
                name=values["name"],
                enabled=enabled_widget.isChecked() if enabled_widget else True,
                min_time=values["min"],
                max_time=values["max"],
                shared_bath=shared
            )
            station = self.model.station(row)
            station.possible_min_process_time = values["possible_min"]
            station.possible_max_process_time = values["possible_max"]
            station.drip_time = values["drip"]
            station.is_process_bath = process_widget.isChecked() if process_widget else True
            validate_station_process_limits(station)

        self.configuration.shared_bath_groups = SharedBathGroupBuilder().build(
            self.configuration.stations
        )
        self.shared_bath_settings_widget.apply_to_configuration(self.configuration)
        return True
