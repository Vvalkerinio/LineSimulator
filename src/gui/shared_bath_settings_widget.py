from PySide6.QtCore import (
    Qt
)

from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QDoubleSpinBox,
    QLabel
)


class SharedBathSettingsWidget(QGroupBox):

    COL_GROUP = 0
    COL_STATIONS = 1
    COL_MODE = 2
    COL_VALUE = 3
    COL_CALCULATED = 4
    COL_DESCRIPTION = 5

    def __init__(
        self,
        parent=None
    ):
        super().__init__(
            "Shared Bath",
            parent
        )

        self.configuration = None

        self._build_ui()

    def _build_ui(
        self
    ):
        layout = QVBoxLayout()

        self.help_label = QLabel(
            "Ustawienie określa, kiedy można załadować kolejną wannę "
            "z tej samej grupy shared bath. "
            "Tryb procentowy wydaje zgodę, gdy poprzednio załadowana "
            "wanna osiągnie wskazany procent minimalnego czasu procesu. "
            "Tryb sekundowy wydaje zgodę po wskazanej liczbie sekund. "
            "Tryb naprzemienny wymusza kolejność: raz jedna wanna, "
            "raz druga wanna w tej samej grupie."
        )

        self.help_label.setWordWrap(
            True
        )

        layout.addWidget(
            self.help_label
        )

        self.table = QTableWidget()
        self.table.setColumnCount(
            6
        )

        self.table.setHorizontalHeaderLabels(
            [
                "Grupa",
                "Stanowiska",
                "Tryb",
                "Wartość",
                "Wyliczone [s]",
                "Wyjaśnienie"
            ]
        )

        layout.addWidget(
            self.table
        )

        self.setLayout(
            layout
        )

    def _group_name(
        self,
        raw
    ):
        if raw is None:
            return ""

        value = str(
            raw
        ).strip()

        if (
            value == ""
            or
            value.lower()
            ==
            "none"
        ):
            return ""

        return value

    def _normalize_mode(
        self,
        mode
    ):
        mode = str(
            mode
        ).strip().lower()

        if mode in [
            "seconds",
            "sekundy",
            "s",
            "sec"
        ]:
            return "seconds"

        if mode in [
            "alternate",
            "alternating",
            "naprzemiennie",
            "raz_jedna_raz_druga"
        ]:
            return "alternate"

        return "percent"

    def _groups_from_configuration(
        self,
        configuration
    ):
        groups = {}

        for station in getattr(
            configuration,
            "stations",
            []
        ):
            if not getattr(
                station,
                "enabled",
                True
            ):
                continue

            group_name = (
                self._group_name(
                    getattr(
                        station,
                        "shared_bath_group",
                        None
                    )
                )
            )

            if not group_name:
                continue

            groups.setdefault(
                group_name,
                []
            ).append(
                station
            )

        return groups

    def _min_process_for_stations(
        self,
        stations
    ):
        values = []

        for station in stations:
            value = float(
                getattr(
                    station,
                    "min_process_time",
                    0.0
                )
            )

            if value > 0.0:
                values.append(
                    value
                )

        if not values:
            return 0.0

        return min(
            values
        )

    def _default_percent(
        self,
        stations
    ):
        if not stations:
            return 0.0

        return (
            100.0
            /
            max(
                1,
                len(
                    stations
                )
            )
        )

    def _station_rule(
        self,
        stations
    ):
        for station in stations:
            mode = getattr(
                station,
                "shared_bath_stagger_mode",
                None
            )

            value = getattr(
                station,
                "shared_bath_stagger_value",
                None
            )

            if (
                mode is not None
                and
                value is not None
            ):
                return (
                    self._normalize_mode(
                        mode
                    ),
                    float(
                        value
                    )
                )

        return (
            "percent",
            self._default_percent(
                stations
            )
        )

    def _make_readonly_item(
        self,
        text
    ):
        item = QTableWidgetItem(
            str(
                text
            )
        )

        item.setFlags(
            item.flags()
            &
            ~Qt.ItemIsEditable
        )

        return item

    def load_from_configuration(
        self,
        configuration
    ):
        self.configuration = configuration

        groups = (
            self._groups_from_configuration(
                configuration
            )
        )

        self.table.setRowCount(
            len(
                groups
            )
        )

        for row, (
            group_name,
            stations
        ) in enumerate(
            sorted(
                groups.items()
            )
        ):
            station_ids = [
                int(
                    station.id
                )
                for station
                in stations
            ]

            mode, value = (
                self._station_rule(
                    stations
                )
            )

            self.table.setItem(
                row,
                self.COL_GROUP,
                self._make_readonly_item(
                    group_name
                )
            )

            self.table.setItem(
                row,
                self.COL_STATIONS,
                self._make_readonly_item(
                    ", ".join(
                        str(
                            station_id
                        )
                        for station_id
                        in station_ids
                    )
                )
            )

            mode_combo = QComboBox()

            mode_combo.addItem(
                "%",
                "percent"
            )

            mode_combo.addItem(
                "sekundy",
                "seconds"
            )

            mode_combo.addItem(
                "naprzemiennie",
                "alternate"
            )

            if mode == "seconds":
                mode_combo.setCurrentIndex(
                    1
                )

            elif mode == "alternate":
                mode_combo.setCurrentIndex(
                    2
                )

            else:
                mode_combo.setCurrentIndex(
                    0
                )

            mode_combo.currentIndexChanged.connect(
                self._recalculate_all_rows
            )

            self.table.setCellWidget(
                row,
                self.COL_MODE,
                mode_combo
            )

            value_spin = QDoubleSpinBox()
            value_spin.setMinimum(
                0.0
            )
            value_spin.setMaximum(
                99999.0
            )
            value_spin.setDecimals(
                1
            )
            value_spin.setSingleStep(
                5.0
            )
            value_spin.setValue(
                float(
                    value
                )
            )

            value_spin.valueChanged.connect(
                self._recalculate_all_rows
            )

            self.table.setCellWidget(
                row,
                self.COL_VALUE,
                value_spin
            )

            self.table.setItem(
                row,
                self.COL_CALCULATED,
                self._make_readonly_item(
                    ""
                )
            )

            self.table.setItem(
                row,
                self.COL_DESCRIPTION,
                self._make_readonly_item(
                    ""
                )
            )

        self._recalculate_all_rows()

        self.table.resizeColumnsToContents()

    def _group_for_row(
        self,
        row
    ):
        item = self.table.item(
            row,
            self.COL_GROUP
        )

        if item is None:
            return ""

        return item.text().strip()

    def _station_ids_for_row(
        self,
        row
    ):
        item = self.table.item(
            row,
            self.COL_STATIONS
        )

        if item is None:
            return []

        values = []

        for raw in item.text().split(
            ","
        ):
            raw = raw.strip()

            if not raw:
                continue

            try:
                values.append(
                    int(
                        raw
                    )
                )

            except Exception:
                pass

        return values

    def _stations_for_row(
        self,
        row
    ):
        if self.configuration is None:
            return []

        station_ids = set(
            self._station_ids_for_row(
                row
            )
        )

        return [
            station
            for station
            in getattr(
                self.configuration,
                "stations",
                []
            )
            if int(
                station.id
            )
            in station_ids
        ]

    def _mode_for_row(
        self,
        row
    ):
        widget = self.table.cellWidget(
            row,
            self.COL_MODE
        )

        if widget is None:
            return "percent"

        return (
            widget.currentData()
            or
            "percent"
        )

    def _value_for_row(
        self,
        row
    ):
        widget = self.table.cellWidget(
            row,
            self.COL_VALUE
        )

        if widget is None:
            return 0.0

        return float(
            widget.value()
        )

    def _calculated_seconds_for_row(
        self,
        row
    ):
        mode = (
            self._mode_for_row(
                row
            )
        )

        if mode == "alternate":
            return 0.0

        stations = (
            self._stations_for_row(
                row
            )
        )

        value = (
            self._value_for_row(
                row
            )
        )

        if mode == "seconds":
            return value

        min_process_time = (
            self._min_process_for_stations(
                stations
            )
        )

        return (
            min_process_time
            *
            value
            /
            100.0
        )

    def _description_for_row(
        self,
        row
    ):
        group_name = (
            self._group_for_row(
                row
            )
        )

        stations = (
            self._stations_for_row(
                row
            )
        )

        station_ids = (
            self._station_ids_for_row(
                row
            )
        )

        mode = (
            self._mode_for_row(
                row
            )
        )

        value = (
            self._value_for_row(
                row
            )
        )

        calculated_seconds = (
            self._calculated_seconds_for_row(
                row
            )
        )

        min_process_time = (
            self._min_process_for_stations(
                stations
            )
        )

        station_text = ", ".join(
            str(
                station_id
            )
            for station_id
            in station_ids
        )

        if mode == "alternate":
            return (
                f"Grupa {group_name} ({station_text}): "
                f"scheduler będzie wybierał wanny naprzemiennie. "
                f"Po załadowaniu jednej wanny następne załadowanie "
                f"tej grupy będzie preferować drugą wannę."
            )

        if mode == "seconds":
            return (
                f"Grupa {group_name} ({station_text}): "
                f"zgoda na załadowanie kolejnej wanny zostanie wydana "
                f"dopiero po upływie {value:.1f} s od ostatniego "
                f"załadunku w tej grupie."
            )

        return (
            f"Grupa {group_name} ({station_text}): "
            f"zgoda na załadowanie kolejnej wanny zostanie wydana "
            f"dopiero, gdy poprzednio załadowana wanna osiągnie "
            f"{value:.1f}% minimalnego czasu procesu. "
            f"Dla min={min_process_time:.1f} s daje to "
            f"{calculated_seconds:.1f} s odstępu."
        )

    def _recalculate_all_rows(
        self
    ):
        for row in range(
            self.table.rowCount()
        ):
            mode = (
                self._mode_for_row(
                    row
                )
            )

            value_widget = self.table.cellWidget(
                row,
                self.COL_VALUE
            )

            if value_widget is not None:
                value_widget.setEnabled(
                    mode != "alternate"
                )

            calculated_seconds = (
                self._calculated_seconds_for_row(
                    row
                )
            )

            if mode == "alternate":
                calculated_text = "-"

            else:
                calculated_text = (
                    f"{calculated_seconds:.1f}"
                )

            self.table.setItem(
                row,
                self.COL_CALCULATED,
                self._make_readonly_item(
                    calculated_text
                )
            )

            self.table.setItem(
                row,
                self.COL_DESCRIPTION,
                self._make_readonly_item(
                    self._description_for_row(
                        row
                    )
                )
            )

        self.table.resizeColumnsToContents()

    def apply_to_configuration(
        self,
        configuration=None
    ):
        if configuration is None:
            configuration = self.configuration

        if configuration is None:
            return

        for row in range(
            self.table.rowCount()
        ):
            group_name = (
                self._group_for_row(
                    row
                )
            )

            if not group_name:
                continue

            mode = (
                self._mode_for_row(
                    row
                )
            )

            value = (
                self._value_for_row(
                    row
                )
            )

            station_ids = set(
                self._station_ids_for_row(
                    row
                )
            )

            for station in getattr(
                configuration,
                "stations",
                []
            ):
                if (
                    int(
                        station.id
                    )
                    not in station_ids
                ):
                    continue

                station.shared_bath_stagger_mode = (
                    mode
                )

                station.shared_bath_stagger_value = (
                    value
                )

        self._recalculate_all_rows()