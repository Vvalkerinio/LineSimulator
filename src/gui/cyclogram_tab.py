from copy import deepcopy
from pathlib import Path
import io
import copy
import traceback
from src.core.synchronized_output import synchronized_redirect_stdout
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
    QSpinBox,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QMessageBox,
    QHeaderView,
    QCheckBox,
    QSplitter,
    QScrollArea,
    QAbstractItemView,
    QSizePolicy,
    QInputDialog
)

from PySide6.QtGui import (
    QColor
)
from PySide6.QtCore import (
    Qt
)
from src.model.station_numbering import (
    STATION_ID_SHIFT,
    display_station_id,
    internal_station_id
)
from src.model.manipulator_program import ManipulatorProgram
from src.model.manipulator_program_step import ManipulatorProgramStep

from src.core.program_driven_simulator import (
    ProgramDrivenSimulator
)

from src.analysis.kpi_engine import (
    KPIEngine
)
from src.analysis.manipulator_program_builder import (
    ManipulatorProgramBuilder
)

from src.analysis.manipulator_program_txt_exporter import (
    ManipulatorProgramTxtExporter
)

from src.analysis.manipulator_program_txt_importer import (
    ManipulatorProgramTxtImporter
)

from src.analysis.program_validator import (
    ProgramValidator
)

from src.analysis.program_consult_generator import (
    ProgramConsultGenerator
)

from src.analysis.program_consult_txt_exporter import (
    ProgramConsultTxtExporter
)
from src.analysis.program_consult_txt_importer import (
    ProgramConsultTxtImporter
)
from src.analysis.material_cycle_window_finder import (
    MaterialCycleWindowFinder
)
from src.analysis.consult_pipeline import (
    ConsultPipeline
)
from src.analysis.iterative_consult_resolver import (
    IterativeConsultResolver
)

class EditableProgramConsult:
    def __init__(self):
        self.source_manipulator_id = 1
        self.source_logical_step_no = 1
        self.source_plc_index = 1
        self.source_word_address = 0
        self.target_manipulator_id = 2
        self.target_logical_step_no = 1
        self.target_plc_index = 1
        self.target_word_address = 0
        self.source_cycle_time_start = 0.0
        self.source_cycle_time_end = 0.0
        self.target_cycle_time_start = 0.0
        self.target_cycle_time_end = 0.0
        self.description = "CONSULT RĘCZNY"

    def to_text(self):
        return (
            f"M{self.source_manipulator_id} INDEX {self.source_plc_index} "
            f"WAIT UNTIL M{self.target_manipulator_id} "
            f"INDEX {self.target_plc_index} FINISHED"
        )


class CyclogramTab(QWidget):

    def __init__(
        self
    ):
        super().__init__()

        self.configuration = None
        self.result = None
        self.programs = {}
        self.consults = []
        self.last_cycle_candidate = None
        self.results_tab = None
        self.gantt_tab = None
        self.trajectory_tab = None
        self.reports_tab = None


        self.index_address_inputs = {}
        self.station_offset_inputs = {}

        self._build_ui()
    def set_configuration(
        self,
        configuration
    ):
        self.configuration = configuration
        self._load_program_settings_from_configuration()
    def _load_program_settings_from_configuration(
        self
    ):
        if self.configuration is None:
            return

        index_addresses = getattr(
            self.configuration,
            "program_index_addresses",
            {
                1: 500,
                2: 600,
                3: 700,
                4: 800
            }
        )

        station_offsets = getattr(
            self.configuration,
            "program_station_offsets",
            {
                1: 0,
                2: 0,
                3: 0,
                4: 0
            }
        )

        for manipulator_id, widget in self.index_address_inputs.items():
            value = index_addresses.get(
                manipulator_id,
                index_addresses.get(
                    str(
                        manipulator_id
                    ),
                    widget.value()
                )
            )

            widget.setValue(
                int(
                    value
                )
            )

        self.transfer_enabled.setChecked(
            bool(getattr(
                self.configuration,
                "program_driven_transfer_enabled",
                True
            ))
        )
        self.transfer_drop_23_delay.setValue(
            float(getattr(
                self.configuration,
                "program_driven_transfer_drop_23_delay",
                0.5
            ))
        )
        self.transfer_pickup_24_delay.setValue(
            float(getattr(
                self.configuration,
                "program_driven_transfer_pickup_24_delay",
                0.5
            ))
        )
        self.transfer_drop_22_delay.setValue(
            float(getattr(
                self.configuration,
                "program_driven_unload_drop_22_delay",
                0.5
            ))
        )

        for manipulator_id, widget in self.station_offset_inputs.items():
            value = station_offsets.get(
                manipulator_id,
                station_offsets.get(
                    str(
                        manipulator_id
                    ),
                    widget.value()
                )
            )

            widget.setValue(
                int(
                    value
                )
            )
    def set_output_tabs(
        self,
        results_tab=None,
        gantt_tab=None,
        trajectory_tab=None,
        reports_tab=None,
        line_overview_tab=None
    ):
        self.results_tab = results_tab
        self.gantt_tab = gantt_tab
        self.trajectory_tab = trajectory_tab
        self.reports_tab = reports_tab
        self.line_overview_tab = line_overview_tab
    def _build_ui(
        self
    ):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(
            6,
            6,
            6,
            6
        )

        view_toolbar = QHBoxLayout()

        self.toggle_settings_button = QPushButton(
            "Ukryj ustawienia"
        )
        self.toggle_settings_button.clicked.connect(
            self._toggle_settings_panel
        )
        view_toolbar.addWidget(
            self.toggle_settings_button
        )

        self.show_all_button = QPushButton(
            "Cały układ"
        )
        self.show_all_button.clicked.connect(
            self._show_all_sections
        )
        view_toolbar.addWidget(
            self.show_all_button
        )

        self.show_program_only_button = QPushButton(
            "Tylko Program PLC"
        )
        self.show_program_only_button.clicked.connect(
            self._show_program_only
        )
        view_toolbar.addWidget(
            self.show_program_only_button
        )

        self.show_consults_only_button = QPushButton(
            "Tylko consulty"
        )
        self.show_consults_only_button.clicked.connect(
            self._show_consults_only
        )
        view_toolbar.addWidget(
            self.show_consults_only_button
        )

        view_toolbar.addStretch()
        main_layout.addLayout(
            view_toolbar
        )

        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(
            True
        )
        self.settings_scroll.setFrameShape(
            QScrollArea.NoFrame
        )
        self.settings_scroll.setMinimumHeight(
            155
        )
        self.settings_scroll.setMaximumHeight(
            330
        )

        self.settings_widget = QWidget()
        settings_layout = QVBoxLayout()
        settings_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )
        settings_layout.addWidget(
            self._build_cycle_controls()
        )
        settings_layout.addWidget(
            self._build_manipulator_program_controls()
        )
        settings_layout.addWidget(
            self._build_transfer_controls()
        )
        settings_layout.addStretch()
        self.settings_widget.setLayout(
            settings_layout
        )
        self.settings_scroll.setWidget(
            self.settings_widget
        )
        main_layout.addWidget(
            self.settings_scroll
        )

        button_layout = QHBoxLayout()
        self.generate_button = QPushButton(
            "Generuj program PLC"
        )
        self.generate_button.clicked.connect(
            self.generate_program
        )
        button_layout.addWidget(
            self.generate_button
        )

        self.find_closed_cycle_button = QPushButton(
            "Znajdź zamknięty cykl"
        )
        self.find_closed_cycle_button.clicked.connect(
            self.find_closed_cycle
        )
        button_layout.addWidget(
            self.find_closed_cycle_button
        )

        self.validate_button = QPushButton(
            "Waliduj program"
        )
        self.validate_button.clicked.connect(
            self.validate_program
        )
        button_layout.addWidget(
            self.validate_button
        )

        self.generate_consults_button = QPushButton(
            "Generuj consulty"
        )
        self.generate_consults_button.clicked.connect(
            self.generate_consults
        )
        button_layout.addWidget(
            self.generate_consults_button
        )

        self.simulate_program_button = QPushButton(
            "Symuluj program PLC"
        )
        self.simulate_program_button.clicked.connect(
            self.simulate_program
        )
        button_layout.addWidget(
            self.simulate_program_button
        )

        self.export_txt_button = QPushButton(
            "Eksport TXT PLC"
        )
        self.export_txt_button.clicked.connect(
            self.export_txt
        )
        button_layout.addWidget(
            self.export_txt_button
        )

        self.export_consults_button = QPushButton(
            "Eksport consultów TXT"
        )
        self.export_consults_button.clicked.connect(
            self.export_consults_txt
        )
        button_layout.addWidget(
            self.export_consults_button
        )

        self.import_consults_button = QPushButton(
            "Import consultów TXT"
        )
        self.import_consults_button.clicked.connect(
            self.import_consults_txt
        )
        button_layout.addWidget(
            self.import_consults_button
        )

        self.import_txt_button = QPushButton(
            "Import TXT"
        )
        self.import_txt_button.clicked.connect(
            self.import_txt
        )
        button_layout.addWidget(
            self.import_txt_button
        )

        self.export_pdf_button = QPushButton(
            "Eksport PDF"
        )
        self.export_pdf_button.clicked.connect(
            self.export_pdf_placeholder
        )
        button_layout.addWidget(
            self.export_pdf_button
        )

        button_layout.addStretch()

        button_widget = QWidget()
        button_widget.setLayout(
            button_layout
        )
        button_scroll = QScrollArea()
        button_scroll.setWidgetResizable(
            True
        )
        button_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )
        button_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        button_scroll.setFrameShape(
            QScrollArea.NoFrame
        )
        button_scroll.setFixedHeight(
            48
        )
        button_scroll.setWidget(
            button_widget
        )
        main_layout.addWidget(
            button_scroll
        )

        self.summary_label = QLabel(
            "Brak programu PLC."
        )
        self.summary_label.setWordWrap(
            True
        )
        main_layout.addWidget(
            self.summary_label
        )

        self.table = QTableWidget()
        self.table.setColumnCount(
            12
        )
        self.table.setHorizontalHeaderLabels(
            [
                "M",
                "IndexPLC",
                "MW ST",
                "Stanowisko",
                "Stanowisko PLC",
                "Akcja",
                "Wait [0.1s]",
                "Wait [s]",
                "Komenda",
                "Źródło",
                "Cel",
                "Status"
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.table.setVerticalScrollMode(
            QAbstractItemView.ScrollPerPixel
        )
        self.table.setHorizontalScrollMode(
            QAbstractItemView.ScrollPerPixel
        )
        self.table.setMinimumHeight(
            220
        )

        program_editor = QHBoxLayout()
        self.add_step_button = QPushButton(
            "Dodaj krok po zaznaczonym"
        )
        self.add_step_button.clicked.connect(
            self.add_program_step
        )
        program_editor.addWidget(
            self.add_step_button
        )

        self.add_new_step_button = QPushButton("Dodaj nowy krok")
        self.add_new_step_button.clicked.connect(self.add_new_program_step)
        program_editor.addWidget(self.add_new_step_button)

        self.add_transfer_sequence_button = QPushButton(
            "Dodaj sekwencję przeładunku"
        )
        self.add_transfer_sequence_button.clicked.connect(
            self.add_transfer_sequence
        )
        program_editor.addWidget(self.add_transfer_sequence_button)

        self.delete_step_button = QPushButton(
            "Usuń krok"
        )
        self.delete_step_button.clicked.connect(
            self.delete_program_step
        )
        program_editor.addWidget(
            self.delete_step_button
        )

        self.move_step_up_button = QPushButton(
            "Krok w górę"
        )
        self.move_step_up_button.clicked.connect(
            self.move_program_step_up
        )
        program_editor.addWidget(
            self.move_step_up_button
        )

        self.move_step_down_button = QPushButton(
            "Krok w dół"
        )
        self.move_step_down_button.clicked.connect(
            self.move_program_step_down
        )
        program_editor.addWidget(
            self.move_step_down_button
        )

        self.apply_steps_button = QPushButton(
            "Zastosuj edycję programu"
        )
        self.apply_steps_button.clicked.connect(
            self.apply_program_table_changes
        )
        program_editor.addWidget(
            self.apply_steps_button
        )
        program_editor.addStretch()

        self.program_panel = QGroupBox(
            "Program PLC"
        )
        program_layout = QVBoxLayout()
        program_layout.addWidget(
            self.table
        )
        program_layout.addLayout(
            program_editor
        )
        self.program_panel.setLayout(
            program_layout
        )

        self.consult_table = QTableWidget()
        self.consult_table.setColumnCount(
            5
        )
        self.consult_table.setHorizontalHeaderLabels(
            [
                "M źródłowy",
                "Index PLC źródłowy",
                "M oczekiwany",
                "Index PLC oczekiwany",
                "Opis"
            ]
        )
        self.consult_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.consult_table.horizontalHeader().setSectionResizeMode(
            4,
            QHeaderView.Stretch
        )
        self.consult_table.setVerticalScrollMode(
            QAbstractItemView.ScrollPerPixel
        )
        self.consult_table.setHorizontalScrollMode(
            QAbstractItemView.ScrollPerPixel
        )
        self.consult_table.setMinimumHeight(
            150
        )

        consult_editor = QHBoxLayout()
        self.add_consult_button = QPushButton(
            "Dodaj consult"
        )
        self.add_consult_button.clicked.connect(
            self.add_consult
        )
        consult_editor.addWidget(
            self.add_consult_button
        )

        self.delete_consult_button = QPushButton(
            "Usuń consult"
        )
        self.delete_consult_button.clicked.connect(
            self.delete_consult
        )
        consult_editor.addWidget(
            self.delete_consult_button
        )

        self.apply_consults_button = QPushButton(
            "Zastosuj edycję consultów"
        )
        self.apply_consults_button.clicked.connect(
            self.apply_consult_table_changes
        )
        consult_editor.addWidget(
            self.apply_consults_button
        )
        consult_editor.addStretch()

        self.consult_panel = QGroupBox(
            "Consulty"
        )
        consult_layout = QVBoxLayout()
        consult_layout.addWidget(
            self.consult_table
        )
        consult_layout.addLayout(
            consult_editor
        )
        self.consult_panel.setLayout(
            consult_layout
        )

        self.data_splitter = QSplitter(
            Qt.Vertical
        )
        self.data_splitter.setChildrenCollapsible(
            False
        )
        self.data_splitter.setHandleWidth(
            8
        )
        self.data_splitter.addWidget(
            self.program_panel
        )
        self.data_splitter.addWidget(
            self.consult_panel
        )
        self.data_splitter.setStretchFactor(
            0,
            3
        )
        self.data_splitter.setStretchFactor(
            1,
            2
        )
        self.data_splitter.setSizes(
            [
                520,
                300
            ]
        )
        self.data_splitter.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        main_layout.addWidget(
            self.data_splitter,
            1
        )

        self.setLayout(
            main_layout
        )

    def _toggle_settings_panel(
        self
    ):
        visible = not self.settings_scroll.isVisible()
        self.settings_scroll.setVisible(
            visible
        )
        self.toggle_settings_button.setText(
            "Ukryj ustawienia"
            if visible
            else "Pokaż ustawienia"
        )

    def _show_all_sections(
        self
    ):
        self.program_panel.setVisible(
            True
        )
        self.consult_panel.setVisible(
            True
        )
        self.data_splitter.setSizes(
            [
                520,
                300
            ]
        )

    def _show_program_only(
        self
    ):
        self.program_panel.setVisible(
            True
        )
        self.consult_panel.setVisible(
            False
        )

    def _show_consults_only(
        self
    ):
        self.program_panel.setVisible(
            False
        )
        self.consult_panel.setVisible(
            True
        )

    def _build_cycle_controls(
        self
    ):
        group = QGroupBox(
            "Okno cyklu"
        )

        layout = QFormLayout()

        self.cycle_start = QDoubleSpinBox()
        self.cycle_start.setMinimum(
            0.0
        )
        self.cycle_start.setMaximum(
            9999999.0
        )
        self.cycle_start.setDecimals(
            1
        )
        self.cycle_start.setSingleStep(
            10.0
        )
        self.cycle_start.setValue(
            1800.0
        )

        layout.addRow(
            "Start cyklu [s]",
            self.cycle_start
        )

        self.cycle_end = QDoubleSpinBox()
        self.cycle_end.setMinimum(
            0.0
        )
        self.cycle_end.setMaximum(
            9999999.0
        )
        self.cycle_end.setDecimals(
            1
        )
        self.cycle_end.setSingleStep(
            10.0
        )
        self.cycle_end.setValue(
            2400.0
        )

        layout.addRow(
            "Koniec cyklu [s]",
            self.cycle_end
        )

        # Numeracja użytkowa jest zawsze zgodna z PLC i zaczyna się od 2.
        # Ukryty adapter zachowuje kompatybilność istniejących builderów.
        self.station_id_shift = QSpinBox()
        self.station_id_shift.setValue(STATION_ID_SHIFT)
        self.station_id_shift.setEnabled(False)
        self.station_id_shift.hide()

        self.max_program_words = QSpinBox()
        self.max_program_words.setMinimum(
            3
        )
        self.max_program_words.setMaximum(
            999
        )
        self.max_program_words.setSingleStep(
            3
        )
        self.max_program_words.setValue(
            99
        )

        layout.addRow(
            "WORD programu",
            self.max_program_words
        )
        self.program_simulation_cycles = QSpinBox()
        self.program_simulation_cycles.setMinimum(
            1
        )
        self.program_simulation_cycles.setMaximum(
            10000
        )
        self.program_simulation_cycles.setValue(
            10
        )

        layout.addRow(
            "Cykle symulacji programu",
            self.program_simulation_cycles
        )

        group.setLayout(
            layout
        )

        return group

    def _build_manipulator_program_controls(
        self
    ):
        group = QGroupBox(
            "Adresy PLC manipulatorów"
        )

        layout = QFormLayout()

        defaults = {
            1: 500,
            2: 600,
            3: 700,
            4: 800
        }

        for manipulator_id in [
            1,
            2,
            3,
            4
        ]:
            row = QHBoxLayout()

            index_input = QSpinBox()
            index_input.setMinimum(
                0
            )
            index_input.setMaximum(
                99999
            )
            index_input.setValue(
                defaults[
                    manipulator_id
                ]
            )

            offset_input = QSpinBox()
            offset_input.setMinimum(
                -100
            )
            offset_input.setMaximum(
                100
            )
            offset_input.setValue(
                0
            )

            row.addWidget(
                QLabel(
                    "MW index"
                )
            )
            row.addWidget(
                index_input
            )

            row.addWidget(
                QLabel(
                    "Offset"
                )
            )
            row.addWidget(
                offset_input
            )

            self.index_address_inputs[
                manipulator_id
            ] = index_input

            self.station_offset_inputs[
                manipulator_id
            ] = offset_input

            index_input.valueChanged.connect(
                self._store_program_settings_in_configuration
            )
            offset_input.valueChanged.connect(
                self._store_program_settings_in_configuration
            )

            layout.addRow(
                f"M{manipulator_id}",
                row
            )

        group.setLayout(
            layout
        )

        return group

    def _store_program_settings_in_configuration(self, _value=None):
        if self.configuration is None:
            return
        self.configuration.program_index_addresses = self._index_addresses()
        self.configuration.program_station_offsets = self._station_offsets()

    def _build_transfer_controls(
        self
    ):
        group = QGroupBox(
            "Przeładunek ProgramDriven przed ST22"
        )
        layout = QFormLayout()

        self.transfer_enabled = QCheckBox(
            "Automatycznie rozwijaj DROP ST22 przez ST23/ST24"
        )
        self.transfer_enabled.setChecked(
            True
        )
        layout.addRow(
            self.transfer_enabled
        )

        self.transfer_drop_23_delay = QDoubleSpinBox()
        self.transfer_drop_23_delay.setRange(
            0.0,
            60.0
        )
        self.transfer_drop_23_delay.setDecimals(
            1
        )
        self.transfer_drop_23_delay.setSingleStep(
            0.1
        )
        self.transfer_drop_23_delay.setValue(
            0.5
        )
        self.transfer_drop_23_delay.setSuffix(
            " s"
        )
        layout.addRow(
            "ST24 OPUSC delay",
            self.transfer_drop_23_delay
        )

        self.transfer_pickup_24_delay = QDoubleSpinBox()
        self.transfer_pickup_24_delay.setRange(
            0.0,
            60.0
        )
        self.transfer_pickup_24_delay.setDecimals(
            1
        )
        self.transfer_pickup_24_delay.setSingleStep(
            0.1
        )
        self.transfer_pickup_24_delay.setValue(
            0.5
        )
        self.transfer_pickup_24_delay.setSuffix(
            " s"
        )
        layout.addRow(
            "ST25 PODNIES delay",
            self.transfer_pickup_24_delay
        )

        self.transfer_drop_22_delay = QDoubleSpinBox()
        self.transfer_drop_22_delay.setRange(
            0.0,
            60.0
        )
        self.transfer_drop_22_delay.setDecimals(
            1
        )
        self.transfer_drop_22_delay.setSingleStep(
            0.1
        )
        self.transfer_drop_22_delay.setValue(
            0.5
        )
        self.transfer_drop_22_delay.setSuffix(
            " s"
        )
        layout.addRow(
            "ST23 OPUSC delay",
            self.transfer_drop_22_delay
        )

        info = QLabel(
            "Każdy materiałowy DROP na ST23 zostanie zastąpiony przez: "
            "ST24 OPUSC, ST25 PODNIES, ST23 OPUSC. "
            "Zmiana jest stosowana tylko w ProgramDriven."
        )
        info.setWordWrap(
            True
        )
        layout.addRow(
            info
        )

        group.setLayout(
            layout
        )
        return group

    def _transfer_wait_01s(
        self,
        spin_box
    ):
        return max(
            0,
            int(round(
                float(spin_box.value())
                * 10.0
            ))
        )

    def _plc_station_value(
        self,
        program,
        station_id
    ):
        return (
            int(station_id)
            - int(program.station_offset)
            + int(program.station_id_shift)
        )

    def _expand_unload_transfer_steps(
        self
    ):
        if not self.transfer_enabled.isChecked():
            return

        drop_23_wait = self._transfer_wait_01s(
            self.transfer_drop_23_delay
        )
        pickup_24_wait = self._transfer_wait_01s(
            self.transfer_pickup_24_delay
        )
        drop_22_wait = self._transfer_wait_01s(
            self.transfer_drop_22_delay
        )

        for program in self.programs.values():
            expanded = []
            for step in program.steps:
                status = str(getattr(
                    step,
                    "status",
                    ""
                ))
                is_unload_drop = (
                    int(getattr(step, "station_id", -1)) == 22
                    and int(getattr(step, "action", 0)) == 2
                    and str(getattr(step, "segment_type", "")) != "empty_parking"
                    and status not in [
                        "TRANSFER_23_DROP",
                        "TRANSFER_24_PICKUP",
                        "UNLOAD_22_DROP"
                    ]
                )
                if not is_unload_drop:
                    expanded.append(step)
                    continue

                step_23 = copy.copy(step)
                step_23.station_id = 23
                step_23.plc_station_value = self._plc_station_value(
                    program,
                    23
                )
                step_23.action = 2
                step_23.wait_time_01s = drop_23_wait
                step_23.command_name = "OPUSC"
                step_23.station_name = "Przeładunek dół"
                step_23.target_station = 23
                step_23.target_name = "Przeładunek dół"
                step_23.status = "TRANSFER_23_DROP"

                step_24 = copy.copy(step)
                step_24.station_id = 24
                step_24.plc_station_value = self._plc_station_value(
                    program,
                    24
                )
                step_24.action = 1
                step_24.wait_time_01s = pickup_24_wait
                step_24.command_name = "PODNIES"
                step_24.station_name = "Przeładunek góra"
                step_24.source_station = 23
                step_24.source_name = "Przeładunek dół"
                step_24.target_station = 24
                step_24.target_name = "Przeładunek góra"
                step_24.status = "TRANSFER_24_PICKUP"

                step_22 = copy.copy(step)
                step_22.station_id = 22
                step_22.plc_station_value = self._plc_station_value(
                    program,
                    22
                )
                step_22.action = 2
                step_22.wait_time_01s = drop_22_wait
                step_22.command_name = "OPUSC"
                step_22.station_name = str(getattr(
                    step,
                    "station_name",
                    "Rozładunek"
                ))
                step_22.source_station = 24
                step_22.source_name = "Przeładunek góra"
                step_22.target_station = 22
                step_22.target_name = step_22.station_name
                step_22.status = "UNLOAD_22_DROP"

                expanded.extend([
                    step_23,
                    step_24,
                    step_22
                ])

            program.steps = expanded
            self._renumber_steps(
                program
            )
            if len(program.steps) * 3 > int(program.max_program_words):
                program.warnings.append(
                    "Sekwencja ST23/ST24 przekracza limit WORD programu: "
                    f"{len(program.steps) * 3} > {program.max_program_words}."
                )

    def update_result(
        self,
        result,
        configuration
    ):
        self.result = result
        self.configuration = configuration
        
        self._load_program_settings_from_configuration()
        steady_state = getattr(
            result,
            "steady_state",
            None
        )

        if isinstance(
            steady_state,
            dict
        ):
            steady_time = (
                steady_state.get(
                    "steady_state_time",
                    None
                )
            )

            if steady_time is not None:
                self.cycle_start.setValue(
                    float(
                        steady_time
                    )
                )

                self.cycle_end.setValue(
                    min(
                        float(
                            getattr(
                                result,
                                "final_time",
                                steady_time
                                +
                                600.0
                            )
                        ),
                        float(
                            steady_time
                        )
                        +
                        600.0
                    )
                )

        self.summary_label.setText(
            "Wynik symulacji dostępny. Ustaw okno cyklu i wygeneruj program PLC."
        )

    def show_tasks(
        self,
        tasks
    ):
        self.summary_label.setText(
            (
                "Legacy show_tasks wywołane. "
                "Nowa zakładka wymaga update_result(result, configuration)."
            )
        )

    def _index_addresses(
        self
    ):
        return {
            manipulator_id:
                widget.value()
            for manipulator_id, widget
            in self.index_address_inputs.items()
        }

    def _station_offsets(
        self
    ):
        return {
            manipulator_id:
                widget.value()
            for manipulator_id, widget
            in self.station_offset_inputs.items()
        }

    def generate_program(
        self
    ):
        if (
            self.result is None
            or
            self.configuration is None
        ):
            QMessageBox.warning(
                self,
                "Program PLC",
                "Najpierw uruchom symulację."
            )
            return

        if (
            self.cycle_end.value()
            <=
            self.cycle_start.value()
        ):
            QMessageBox.warning(
                self,
                "Program PLC",
                "Koniec cyklu musi być większy niż start."
            )
            return

        builder = ManipulatorProgramBuilder(
            configuration=(
                self.configuration
            ),
            result=(
                self.result
            ),
            cycle_start_time=(
                self.cycle_start.value()
            ),
            cycle_end_time=(
                self.cycle_end.value()
            ),
            index_addresses_by_manipulator=(
                self._index_addresses()
            ),
            station_offsets_by_manipulator=(
                self._station_offsets()
            ),
            station_id_shift=(
                STATION_ID_SHIFT
            ),
            max_program_words=(
                self.max_program_words.value()
            )
        )

        self.programs = (
            builder.build()
        )
        self._expand_unload_transfer_steps()

        self.consults = []

        self._refresh_table()
        self._select_table_row(self.table, len(program.steps)-1)
        self._refresh_consult_table()

    def validate_program(
        self
    ):
        if not self.programs:
            QMessageBox.warning(
                self,
                "Walidacja",
                "Najpierw wygeneruj lub zaimportuj program PLC."
            )
            return

        validator = ProgramValidator()

        validation = (
            validator.validate(
                self.programs
            )
        )

        lines = []

        if validation.valid:
            lines.append(
                "PROGRAM POPRAWNY"
            )

        else:
            lines.append(
                "PROGRAM ZAWIERA BŁĘDY"
            )

        lines.append(
            ""
        )

        for message in validation.messages:
            lines.append(
                (
                    f"[{message.level}] "
                    f"M{message.manipulator_id} "
                    f"{message.code} "
                    f"- "
                    f"{message.message}"
                )
            )

        QMessageBox.information(
            self,
            "Wynik walidacji",
            "\n".join(
                lines
            )
        )

    def generate_consults(
        self
    ):
        if (
            self.configuration is None
            or
            not self.programs
        ):
            QMessageBox.warning(
                self,
                "Consulty",
                "Najpierw wygeneruj program PLC."
            )
            return

        initial_station_occupancy = None
        initial_manipulator_positions = None
        if hasattr(
            self,
            "_initial_station_occupancy_for_program_simulation"
        ):
            initial_station_occupancy = (
                self._initial_station_occupancy_for_program_simulation()
            )
            initial_manipulator_positions = (
                self._initial_manipulator_positions_for_program_simulation()
            )
        

        if hasattr(
            self,
            "_initial_manipulator_positions_for_program_simulation"
        ):
            initial_manipulator_positions = (
                self._initial_manipulator_positions_for_program_simulation()
            )

        print()
        print("=" * 80)
        print("ITERATIVE CONSULT RESOLUTION")
        print("=" * 80)

        print(
            "Initial occupancy: "
            f"{sorted(initial_station_occupancy.items()) if initial_station_occupancy else 'heuristic'}"
        )
        print(
            "Initial manipulator positions: "
            f"{sorted(initial_manipulator_positions.items()) if initial_manipulator_positions else 'configuration'}"
        )

        resolver = IterativeConsultResolver(
            configuration=(
                self.configuration
            ),
            programs=(
                self.programs
            ),
            cycles=(
                self.program_simulation_cycles.value()
            ),
            initial_station_occupancy=(
                initial_station_occupancy
            ),
            initial_manipulator_positions=(
                initial_manipulator_positions
            ),
            max_iterations=(
                40
            ),
            include_material_consults=(
                True
            )
        )

        resolution = (
            resolver.resolve()
        )

        self.consults = (
            resolution.consults
        )

        self.program_simulation_result = (
            resolution.simulation_result
        )

        print()
        print("=" * 80)
        print("ITERATIVE CONSULT RESULT")
        print("=" * 80)

        print(
            f"Iterations       : "
            f"{resolution.iterations}"
        )

        print(
            f"Stopped reason   : "
            f"{resolution.stopped_reason}"
        )

        print(
            f"Consults         : "
            f"{len(self.consults)}"
        )

        print(
            f"Skipped consults : "
            f"{len(resolution.skipped_consults)}"
        )

        if resolution.simulation_result is not None:
            print(
                f"Empty pickup warn: "
                f"{len(getattr(resolution.simulation_result, 'empty_pickup_warnings', []))}"
            )

            print(
                f"Occupied drop warn: "
                f"{len(getattr(resolution.simulation_result, 'occupied_drop_warnings', []))}"
            )

            print(
                f"Track waits      : "
                f"{len(getattr(resolution.simulation_result, 'track_waits', []))}"
            )

        print("=" * 80)

        print()
        print("=" * 80)
        print("GENERATED CONSULTS")
        print("=" * 80)

        for consult in self.consults:
            print(
                consult.to_text()
            )

        print("=" * 80)
        print(
            f"TOTAL CONSULTS: {len(self.consults)}"
        )
        print("=" * 80)

        if (
            self.trajectory_tab is not None
            and
            resolution.simulation_result is not None
        ):
            if hasattr(
                self.trajectory_tab,
                "update_program_result"
            ):
                self.trajectory_tab.update_program_result(
                    resolution.simulation_result
                )

        QMessageBox.information(
            self,
            "Consulty",
            (
                "Zakończono iteracyjne generowanie consultów.\n\n"
                f"Iteracje: {resolution.iterations}\n"
                f"Powód stopu: {resolution.stopped_reason}\n"
                f"Consulty: {len(self.consults)}\n"
                f"Pominięte przez cykle: {len(resolution.skipped_consults)}"
            )
        )
    def _manipulator_color(self, manipulator_id):
        colors = {
            1: QColor(205, 225, 255),
            2: QColor(205, 245, 215),
            3: QColor(255, 225, 195),
            4: QColor(230, 210, 250)
        }
        return colors.get(
            int(manipulator_id),
            QColor(245, 245, 245)
        )

    def _manipulator_text_color(self, manipulator_id):
        colors = {
            1: QColor(20, 70, 150),
            2: QColor(20, 115, 55),
            3: QColor(165, 75, 10),
            4: QColor(105, 45, 145)
        }
        return colors.get(
            int(manipulator_id),
            QColor(25, 25, 25)
        )

    def _manipulator_combo(self, manipulator_id):
        combo = QComboBox()
        for candidate_id in [1, 2, 3, 4]:
            combo.addItem(
                f"M{candidate_id}",
                candidate_id
            )
            item_index = combo.count() - 1
            combo.setItemData(
                item_index,
                self._manipulator_color(candidate_id),
                Qt.BackgroundRole
            )
            combo.setItemData(
                item_index,
                self._manipulator_text_color(candidate_id),
                Qt.ForegroundRole
            )
        selected_index = combo.findData(
            int(manipulator_id)
        )
        combo.setCurrentIndex(
            max(0, selected_index)
        )
        self._style_manipulator_combo(combo)
        combo.currentIndexChanged.connect(
            lambda _index, widget=combo:
                self._style_manipulator_combo(widget)
        )
        return combo

    def _style_manipulator_combo(self, combo):
        manipulator_id = int(combo.currentData())
        background = self._manipulator_color(manipulator_id)
        foreground = self._manipulator_text_color(manipulator_id)
        combo.setStyleSheet(
            "QComboBox {"
            f"background-color: rgb({background.red()}, {background.green()}, {background.blue()});"
            f"color: rgb({foreground.red()}, {foreground.green()}, {foreground.blue()});"
            "font-weight: bold;"
            "padding: 2px 6px;"
            "}"
        )

    def _combo_manipulator_id(self, table, row, column, field_name):
        combo = table.cellWidget(
            row,
            column
        )
        if combo is None:
            raise ValueError(
                f"Wiersz {row + 1}: brak listy {field_name}."
            )
        return int(combo.currentData())

    def _program_rows(self):
        rows = []
        for manipulator_id in sorted(self.programs.keys()):
            program = self.programs[manipulator_id]
            for step in program.steps:
                rows.append((program, step))
        return rows

    def _renumber_steps(self, program):
        for number, step in enumerate(program.steps, start=1):
            step.step_no = number

    def _selected_program_item(self, warn=True):
        row = self.table.currentRow()
        rows = self._program_rows()
        if row < 0 or row >= len(rows):
            if warn:
                QMessageBox.warning(self, "Edycja programu", "Zaznacz krok programu.")
            return None
        return rows[row]

    def _choose_program_manipulator(self):
        selected, accepted = QInputDialog.getItem(
            self, "Program PLC", "Manipulator:",
            ["M1", "M2", "M3", "M4"], 0, False
        )
        return int(selected[1:]) if accepted else None

    def _ensure_program(self, manipulator_id):
        manipulator_id = int(manipulator_id)
        if manipulator_id not in self.programs:
            self.programs[manipulator_id] = ManipulatorProgram(
                manipulator_id=manipulator_id,
                index_address=int(self._index_addresses().get(manipulator_id, 0)),
                station_offset=int(self._station_offsets().get(manipulator_id, 0)),
                station_id_shift=int(STATION_ID_SHIFT)
            )
        return self.programs[manipulator_id]

    def _manual_step(self, program, station_id, action, wait, status):
        station_id = int(station_id)
        return ManipulatorProgramStep(
            manipulator_id=int(program.manipulator_id),
            step_no=len(program.steps) + 1,
            cycle_time_start=0.0,
            cycle_time_end=0.0,
            station_id=station_id,
            plc_station_value=self._plc_station_value(program, station_id),
            action=int(action),
            wait_time_01s=int(wait),
            command_name="PICKUP" if int(action) == 1 else "DROP",
            station_name=f"ST{station_id}",
            source_station=station_id if int(action) == 1 else None,
            target_station=station_id if int(action) == 2 else None,
            source_name=f"ST{station_id}" if int(action) == 1 else "",
            target_name=f"ST{station_id}" if int(action) == 2 else "",
            segment_type="manual",
            status=status
        )


    def _select_table_row(self, table, row):
        if table.rowCount() <= 0:
            return
        row = max(0, min(int(row), table.rowCount() - 1))
        table.setCurrentCell(row, 0)
        table.selectRow(row)

    def add_new_program_step(self):
        selected = self._selected_program_item(warn=False)
        if selected is None:
            manipulator_id = self._choose_program_manipulator()
            if manipulator_id is None:
                return
            program = self._ensure_program(manipulator_id)
        else:
            program = selected[0]
        program.steps.append(self._manual_step(program, 1, 1, 0, "MANUAL_ADDED"))
        self._renumber_steps(program)
        self._refresh_table()

    def add_transfer_sequence(self):
        selected = self._selected_program_item(warn=False)
        if selected is None:
            manipulator_id = self._choose_program_manipulator()
            if manipulator_id is None:
                return
            program = self._ensure_program(manipulator_id)
            insert_at = len(program.steps)
        else:
            program, step = selected
            insert_at = program.steps.index(step) + 1
        steps = [
            self._manual_step(program, 23, 2, self._transfer_wait_01s(self.transfer_drop_23_delay), "TRANSFER_23_DROP"),
            self._manual_step(program, 24, 1, self._transfer_wait_01s(self.transfer_pickup_24_delay), "TRANSFER_24_PICKUP"),
            self._manual_step(program, 22, 2, self._transfer_wait_01s(self.transfer_drop_22_delay), "UNLOAD_22_DROP")
        ]
        program.steps[insert_at:insert_at] = steps
        self._renumber_steps(program)
        self._refresh_table()

    def add_program_step(self):
        selected = self._selected_program_item()
        if selected is None:
            return
        program, step = selected
        new_step = copy.copy(step)
        new_step.status = "MANUAL_ADDED"
        index = program.steps.index(step)
        program.steps.insert(index + 1, new_step)
        self._renumber_steps(program)
        self._refresh_table()
        self._select_table_row(self.table, index + 1)

    def delete_program_step(self):
        selected = self._selected_program_item()
        if selected is None:
            return
        program, step = selected
        index = program.steps.index(step)
        program.steps.remove(step)
        self._renumber_steps(program)
        self._refresh_table()
        self._select_table_row(self.table, index)

    def _move_program_step(self, offset):
        selected = self._selected_program_item()
        if selected is None:
            return
        program, step = selected
        index = program.steps.index(step)
        target = index + offset
        if target < 0 or target >= len(program.steps):
            return
        program.steps[index], program.steps[target] = (
            program.steps[target],
            program.steps[index]
        )
        self._renumber_steps(program)
        self._refresh_table()
        self._select_table_row(self.table, target)

    def move_program_step_up(self):
        self._move_program_step(-1)

    def move_program_step_down(self):
        self._move_program_step(1)

    def _int_text(self, item, name):
        if item is None:
            raise ValueError(f"Brak wartości: {name}")
        text = item.text().strip()
        if text.startswith("MW"):
            text = text[2:]
        elif text.startswith("M"):
            text = text[1:]
        return int(text)

    def _float_text(self, item, name):
        if item is None:
            raise ValueError(f"Brak wartości: {name}")
        return float(item.text().strip().replace(",", "."))

    def apply_program_table_changes(self, show_message=True):
        rows = self._program_rows()
        if len(rows) != self.table.rowCount():
            self._refresh_table()
            return False

        names = {
            int(station.id): station.name
            for station in getattr(self.configuration, "stations", [])
        }
        migrations = []
        try:
            for row, (source_program, step) in enumerate(rows):
                target_manipulator_id = self._combo_manipulator_id(
                    self.table,
                    row,
                    0,
                    "manipulatora"
                )
                target_program = self.programs.get(
                    target_manipulator_id
                )
                if target_program is None:
                    raise ValueError(
                        f"Wiersz {row + 1}: brak programu M{target_manipulator_id}."
                    )

                displayed_station_id = self._int_text(
                    self.table.item(row, 3),
                    "Stanowisko"
                )
                station_id = internal_station_id(displayed_station_id)
                plc_station = self._plc_station_value(target_program, station_id)
                action = self._int_text(
                    self.table.item(row, 5),
                    "Akcja"
                )
                wait_value = self._int_text(
                    self.table.item(row, 6),
                    "WAIT"
                )
                if action not in [1, 2]:
                    raise ValueError(
                        f"Wiersz {row + 1}: akcja musi być 1 lub 2."
                    )
                if wait_value < 0:
                    raise ValueError(
                        f"Wiersz {row + 1}: WAIT nie może być ujemny."
                    )

                step.manipulator_id = target_manipulator_id
                step.plc_station_value = plc_station
                step.station_id = station_id
                step.target_station = station_id
                step.action = action
                step.wait_time_01s = wait_value
                step.command_name = "PODNIES" if action == 1 else "OPUSC"
                step.station_name = names.get(station_id, f"S{station_id}")
                step.target_name = step.station_name
                step.status = "MANUAL_EDITED"

                if source_program is not target_program:
                    migrations.append((
                        source_program,
                        target_program,
                        step
                    ))

            for source_program, target_program, step in migrations:
                if step in source_program.steps:
                    source_program.steps.remove(step)
                if step not in target_program.steps:
                    target_program.steps.append(step)

            for program in self.programs.values():
                self._renumber_steps(program)
        except Exception as error:
            QMessageBox.critical(
                self,
                "Edycja programu",
                str(error)
            )
            return False

        self._refresh_table()
        if show_message:
            QMessageBox.information(
                self,
                "Edycja programu",
                "Zmiany zastosowano. Przeniesione rozkazy zostały ponownie ponumerowane."
            )
        return True

    def add_consult(self):
        row = self.consult_table.currentRow()
        if 0 <= row < len(self.consults):
            consult = copy.copy(self.consults[row])
            consult.description = (
                str(getattr(consult, "description", "")) + " KOPIA RĘCZNA"
            ).strip()
        else:
            consult = EditableProgramConsult()
        self.consults.append(consult)
        self._refresh_consult_table()
        self._select_table_row(self.consult_table, len(self.consults)-1)

    def delete_consult(self):
        row = self.consult_table.currentRow()
        if row < 0 or row >= len(self.consults):
            QMessageBox.warning(self, "Edycja consultów", "Zaznacz consult.")
            return
        del self.consults[row]
        self._refresh_consult_table()
        self._select_table_row(self.consult_table, row)

    def _program_for_manipulator(
        self,
        manipulator_id
    ):
        return self.programs.get(
            int(manipulator_id)
        )

    def _logical_step_for_plc_index(
        self,
        plc_index
    ):
        return (
            (int(plc_index) - 1)
            // 3
            + 1
        )

    def _word_address_for_consult(
        self,
        manipulator_id,
        plc_index
    ):
        program = self._program_for_manipulator(
            manipulator_id
        )
        if program is None:
            raise ValueError(
                f"Brak programu M{manipulator_id}."
            )
        max_index = len(program.steps) * 3
        if plc_index < 1 or plc_index > max_index:
            raise ValueError(
                f"Index {plc_index} nie istnieje w programie M{manipulator_id}; "
                f"zakres 1..{max_index}."
            )
        return int(program.index_address) + int(plc_index)

    def apply_consult_table_changes(self, show_message=True):
        if self.consult_table.rowCount() != len(self.consults):
            self._refresh_consult_table()
            return False
        seen = set()
        try:
            for row, consult in enumerate(self.consults):
                source_m = self._combo_manipulator_id(
                    self.consult_table,
                    row,
                    0,
                    "manipulatora źródłowego"
                )
                source_index = self._int_text(
                    self.consult_table.item(row, 1),
                    "Index PLC źródłowy"
                )
                target_m = self._combo_manipulator_id(
                    self.consult_table,
                    row,
                    2,
                    "manipulatora oczekiwanego"
                )
                target_index = self._int_text(
                    self.consult_table.item(row, 3),
                    "Index PLC oczekiwany"
                )
                description_item = self.consult_table.item(
                    row,
                    4
                )
                description = (
                    description_item.text().strip()
                    if description_item is not None
                    else "CONSULT RĘCZNY"
                )

                if source_m == target_m and source_index == target_index:
                    raise ValueError(
                        f"Wiersz {row + 1}: consult czeka sam na siebie."
                    )

                key = (
                    source_m,
                    source_index,
                    target_m,
                    target_index
                )
                if key in seen:
                    raise ValueError(
                        f"Wiersz {row + 1}: zduplikowany consult."
                    )
                seen.add(key)

                consult.source_manipulator_id = source_m
                consult.source_plc_index = source_index
                consult.source_logical_step_no = self._logical_step_for_plc_index(
                    source_index
                )
                consult.source_word_address = self._word_address_for_consult(
                    source_m,
                    source_index
                )
                consult.target_manipulator_id = target_m
                consult.target_plc_index = target_index
                consult.target_logical_step_no = self._logical_step_for_plc_index(
                    target_index
                )
                consult.target_word_address = self._word_address_for_consult(
                    target_m,
                    target_index
                )
                consult.description = description
        except Exception as error:
            QMessageBox.critical(
                self,
                "Edycja consultów",
                str(error)
            )
            return False
        self._refresh_consult_table()
        if show_message:
            QMessageBox.information(
                self,
                "Edycja consultów",
                "Zmiany zastosowano. Kroki logiczne i MW przeliczono automatycznie."
            )
        return True

    def _refresh_table(self):
        rows = self._program_rows()
        self.table.clearContents()
        self.table.setRowCount(len(rows))

        for row, (program, step) in enumerate(rows):
            base_address = program.index_address + 1 + (step.step_no - 1) * 3
            plc_index = (step.step_no - 1) * 3 + 1
            values = [
                None,
                str(plc_index),
                f"MW{base_address}",
                str(display_station_id(step.station_id)),
                str(step.plc_station_value),
                str(step.action),
                str(step.wait_time_01s),
                f"{step.wait_time_01s / 10.0:.1f}",
                step.command_name,
                self._display_station_text(step.source_name),
                self._display_station_text(step.target_name),
                self._display_station_text(step.status)
            ]

            combo = self._manipulator_combo(
                step.manipulator_id
            )
            self.table.setCellWidget(
                row,
                0,
                combo
            )

            row_background = self._manipulator_color(
                step.manipulator_id
            )
            row_foreground = self._manipulator_text_color(
                step.manipulator_id
            )
            for column in range(1, len(values)):
                cell = QTableWidgetItem(
                    values[column]
                )
                if column not in [3, 5, 6]:
                    cell.setFlags(
                        cell.flags()
                        & ~Qt.ItemIsEditable
                    )
                cell.setBackground(
                    row_background
                )
                cell.setForeground(
                    row_foreground
                )
                if column in [1, 2, 8]:
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
                self.table.setItem(
                    row,
                    column,
                    cell
                )

        warning_count = sum(
            len(program.warnings)
            for program in self.programs.values()
        )
        step_count = sum(
            len(program.steps)
            for program in self.programs.values()
        )
        self.summary_label.setText(
            f"Wygenerowano {step_count} kroków PLC. "
            f"Ostrzeżenia: {warning_count}. Consulty: {len(self.consults)}."
        )
        self.table.resizeColumnsToContents()

    def _display_station_text(self, text):
        import re
        text = str(text or "")
        def repl(match):
            from src.model.station_numbering import display_station_id
            return f"ST{display_station_id(int(match.group(1)))}"
        return re.sub(r"ST(\d+)", repl, text)

    def _refresh_consult_table(
        self
    ):
        self.consult_table.clearContents()
        self.consult_table.setRowCount(
            len(self.consults)
        )
        for row, consult in enumerate(self.consults):
            source_manipulator_id = int(
                consult.source_manipulator_id
            )
            target_manipulator_id = int(
                consult.target_manipulator_id
            )

            self.consult_table.setCellWidget(
                row,
                0,
                self._manipulator_combo(source_manipulator_id)
            )
            self.consult_table.setCellWidget(
                row,
                2,
                self._manipulator_combo(target_manipulator_id)
            )

            values = {
                1: str(consult.source_plc_index),
                3: str(consult.target_plc_index),
                4: str(getattr(consult, "description", ""))
            }
            source_background = self._manipulator_color(
                source_manipulator_id
            )
            target_background = self._manipulator_color(
                target_manipulator_id
            )
            for column, value in values.items():
                cell = QTableWidgetItem(value)
                if column == 1:
                    cell.setBackground(source_background)
                    cell.setForeground(
                        self._manipulator_text_color(source_manipulator_id)
                    )
                elif column == 3:
                    cell.setBackground(target_background)
                    cell.setForeground(
                        self._manipulator_text_color(target_manipulator_id)
                    )
                else:
                    cell.setBackground(QColor(255, 250, 210))
                self.consult_table.setItem(
                    row,
                    column,
                    cell
                )
        self.consult_table.resizeColumnsToContents()

    def export_txt(
        self
    ):
        if not self.programs:
            QMessageBox.warning(
                self,
                "Eksport TXT",
                "Najpierw wygeneruj program PLC."
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Eksport programu PLC",
            "manipulator_program.txt",
            "Text files (*.txt)"
        )

        if not path:
            return

        ManipulatorProgramTxtExporter(
            self.programs
        ).save(
            path
        )

        QMessageBox.information(
            self,
            "Eksport TXT",
            "Program PLC został zapisany."
        )

    def export_consults_txt(
        self
    ):
        if not self.consults:
            QMessageBox.warning(
                self,
                "Eksport consultów",
                "Najpierw wygeneruj consulty."
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Eksport consultów",
            "manipulator_consults.txt",
            "Text files (*.txt)"
        )

        if not path:
            return

        ProgramConsultTxtExporter(
            self.consults
        ).save(
            path
        )

        QMessageBox.information(
            self,
            "Eksport consultów",
            "Consulty zostały zapisane."
        )

    def import_txt(
        self
    ):
        # Źródłem prawdy dla importu są bieżące wartości QSpinBox,
        # nie wartości domyślne ani wcześniejszy stan konfiguracji.
        index_addresses = {
            int(manipulator_id): int(widget.value())
            for manipulator_id, widget
            in self.index_address_inputs.items()
        }
        station_offsets = {
            int(manipulator_id): int(widget.value())
            for manipulator_id, widget
            in self.station_offset_inputs.items()
        }

        if len(index_addresses) != 4:
            QMessageBox.critical(
                self,
                "Import TXT",
                "Nie odczytano czterech adresów MW Index z GUI."
            )
            return

        if len(set(index_addresses.values())) != len(index_addresses):
            QMessageBox.critical(
                self,
                "Import TXT",
                "Adresy MW Index manipulatorów muszą być unikalne."
            )
            return

        self.configuration.program_index_addresses = dict(
            index_addresses
        )
        self.configuration.program_station_offsets = dict(
            station_offsets
        )

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import programu PLC",
            str(Path(__file__).resolve().parents[2] / "examples" / "plc"),
            "Text files (*.txt)"
        )

        if not path:
            return

        importer = ManipulatorProgramTxtImporter(
            index_addresses_by_manipulator=index_addresses,
            station_offsets_by_manipulator=station_offsets,
            station_id_shift=int(
                STATION_ID_SHIFT
            ),
            max_program_words=int(
                self.max_program_words.value()
            )
        )

        try:
            self.programs = importer.import_file(
                path
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Import TXT",
                f"Błąd importu programu PLC:\n{error}"
            )
            return

        self.consults = []
        self._refresh_table()
        self._refresh_consult_table()

        range_lines = []
        for manipulator_id in sorted(index_addresses):
            index_address = index_addresses[manipulator_id]
            range_lines.append(
                f"M{manipulator_id}: MW Index={index_address}, "
                f"program MW{index_address + 1}.."
                f"MW{index_address + self.max_program_words.value()}"
            )

        QMessageBox.information(
            self,
            "Import TXT",
            "Program PLC został zaimportowany z adresów wpisanych w GUI.\n\n"
            + "\n".join(range_lines)
        )

    def import_consults_txt(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import consultów",
            str(Path(__file__).resolve().parents[2] / "examples" / "consults"),
            "Text files (*.txt)"
        )
        if not path:
            return

        imported = ProgramConsultTxtImporter().import_file(path)
        if not imported:
            QMessageBox.warning(
                self,
                "Import consultów",
                "Nie znaleziono poprawnych komend consultów w pliku."
            )
            return

        self.consults = imported
        if self.programs and not self.apply_consult_table_changes(show_message=False):
            return
        self._refresh_consult_table()
        QMessageBox.information(
            self,
            "Import consultów",
            f"Zaimportowano consulty: {len(self.consults)}."
        )

    def simulate_program(
        self
    ):
        if not self.programs:
            QMessageBox.warning(
                self,
                "Symulacja programu",
                "Najpierw wygeneruj albo zaimportuj program PLC."
            )
            return

        if self.configuration is None:
            QMessageBox.warning(
                self,
                "Symulacja programu",
                "Brak konfiguracji linii."
            )
            return

        if not self.apply_program_table_changes(show_message=False):
            return
        if not self.apply_consult_table_changes(show_message=False):
            return

        buffer = io.StringIO()

        with synchronized_redirect_stdout(buffer):
            try:
                print(
                    "PROGRAM USING EMPTY INITIAL LINE AND CONFIGURATION "
                    "MANIPULATOR POSITIONS"
                )

                simulator = ProgramDrivenSimulator(
                    configuration=(
                        deepcopy(self.configuration)
                    ),
                    programs=(
                        self.programs
                    ),
                    consults=(
                        self.consults
                    ),
                    cycles=(
                        self.program_simulation_cycles.value()
                    ),
                    initial_state_mode=(
                        ProgramDrivenSimulator.INITIAL_STATE_EMPTY
                    )
                )

                result = (
                    simulator.run()
                )

                print()
                print(
                    "=" * 60
                )
                print(
                    "PROGRAM DRIVEN SIMULATION"
                )
                print(
                    "=" * 60
                )
                print(
                    f"Cycles            : "
                    f"{self.program_simulation_cycles.value()}"
                )
                print(
                    f"Events            : "
                    f"{len(result.events)}"
                )
                print(
                    f"Tasks             : "
                    f"{len(result.manipulator_tasks)}"
                )
                print(
                    f"Generated hangers : "
                    f"{result.generated_hangers}"
                )
                print(
                    f"Prefilled hangers : "
                    f"{getattr(result, 'prefilled_hangers', 0)}"
                )
                                
                print(
                    f"Final time        : "
                    f"{result.final_time:.1f}s"
                )
                print(
                    f"Consults          : "
                    f"{len(self.consults)}"
                )
                print(
                    f"Empty pickup warn : "
                    f"{len(getattr(result, 'empty_pickup_warnings', []))}"
                )

                print(
                    f"Occupied drop warn: "
                    f"{len(getattr(result, 'occupied_drop_warnings', []))}"
                )
                print(
                    f"Track waits       : "
                    f"{len(getattr(result, 'track_waits', []))}"
                )
                print(
                    "=" * 60
                )
                

                from src.analysis.lead_time_report import (
                    LeadTimeReport
                )

                LeadTimeReport().print_summary(
                    result
                )

                from src.analysis.event_diagnostics import (
                    EventDiagnostics
                )

                EventDiagnostics().print_summary(
                    result
                )

                from src.analysis.process_compliance_report import (
                    ProcessComplianceReport
                )

                ProcessComplianceReport().print_summary(
                    result
                )

                from src.analysis.manipulator_utilization_report import (
                    ManipulatorUtilizationReport
                )

                ManipulatorUtilizationReport().print_summary(
                    result,
                    self.configuration
                )

                from src.analysis.station_residence_report import (
                    StationResidenceReport
                )

                StationResidenceReport().print_summary(
                    result,
                    self.configuration
                )

                from src.analysis.manipulator_separation_report import (
                    ManipulatorSeparationReport
                )

                ManipulatorSeparationReport().print_summary(
                    result,
                    self.configuration
                )

                kpi = (
                    KPIEngine()
                    .calculate(
                        result,
                        getattr(self.configuration, "pieces_per_transport", 7)
                    )
                )

                if self.results_tab is not None:
                    self.results_tab.show_results(
                        result,
                        kpi
                    )

                if self.gantt_tab is not None:
                    self.gantt_tab.update_result(
                        result
                    )

                if self.trajectory_tab is not None:
                    if hasattr(
                        self.trajectory_tab,
                        "update_program_result"
                    ):
                        self.trajectory_tab.update_program_result(
                            result
                        )
                    else:
                        self.trajectory_tab.update_result(
                            result
                        )
                if self.line_overview_tab is not None:
                    self.line_overview_tab.update_result(
                        result
                    )
                if self.reports_tab is not None:
                    self.reports_tab.show_report_text(
                        buffer.getvalue()
                    )

                self.result = (
                    result
                )

                self.summary_label.setText(
                    (
                        f"Zasymulowano program PLC. "
                        f"Tasks={len(result.manipulator_tasks)}, "
                        f"Final={result.final_time:.1f}s, "
                        f"Consults={len(self.consults)}."
                    )
                )

            except Exception:
                print()
                print(
                    "=" * 60
                )
                print(
                    "PROGRAM SIMULATION ERROR"
                )
                print(
                    "=" * 60
                )
                print(
                    traceback.format_exc()
                )

                if self.reports_tab is not None:
                    self.reports_tab.show_report_text(
                        buffer.getvalue()
                    )

                QMessageBox.critical(
                    self,
                    "Symulacja programu",
                    "Błąd symulacji programu. Szczegóły są w zakładce Raporty."
                )
    def export_pdf_placeholder(
        self
    ):
        QMessageBox.information(
            self,
            "Eksport PDF",
            (
                "Eksport PDF dodamy w następnym kroku. "
                "Aktualnie gotowy jest eksport TXT PLC oraz TXT consultów."
            )
        )
    def apply_to_configuration(
        self
    ):
        if self.configuration is None:
            return

        self.configuration.program_index_addresses = (
            self._index_addresses()
        )

        self.configuration.program_station_offsets = (
            self._station_offsets()
        )
        self.configuration.program_driven_transfer_enabled = (
            self.transfer_enabled.isChecked()
        )
        self.configuration.program_driven_transfer_drop_23_delay = (
            self.transfer_drop_23_delay.value()
        )
        self.configuration.program_driven_transfer_pickup_24_delay = (
            self.transfer_pickup_24_delay.value()
        )
        self.configuration.program_driven_unload_drop_22_delay = (
            self.transfer_drop_22_delay.value()
        )
    def _format_candidate_details(
        self,
        candidate
    ):
        lines = []

        lines.append(
            candidate.summary()
        )

        lines.append(
            ""
        )

        lines.append(
            "Transporty na manipulator:"
        )

        for manipulator_id, count in candidate.transport_counts_by_manipulator.items():
            lines.append(
                f"M{manipulator_id}: {count}"
            )

        lines.append(
            ""
        )

        lines.append(
            "Kroki logiczne na manipulator:"
        )

        for manipulator_id, count in candidate.logical_steps_by_manipulator.items():
            lines.append(
                f"M{manipulator_id}: {count}"
            )

        lines.append(
            ""
        )

        if candidate.balance:
            lines.append(
                "Niezamknięty bilans:"
            )

            for station_id, value in candidate.balance.items():
                lines.append(
                    f"S{station_id}: {value}"
                )

        else:
            lines.append(
                "Bilans materiałowy: OK"
            )

        lines.append(
            ""
        )

        if candidate.phase_errors:
            lines.append(
                "Błędy fazy stanowisk:"
            )

            for message in candidate.phase_errors[
                :20
            ]:
                lines.append(
                    f"- {message}"
                )

            if (
                len(
                    candidate.phase_errors
                )
                >
                20
            ):
                lines.append(
                    (
                        f"... oraz "
                        f"{len(candidate.phase_errors) - 20} "
                        f"kolejnych błędów fazy."
                    )
                )

        else:
            lines.append(
                "Faza stanowisk: OK"
            )

        lines.append(
            ""
        )

        lines.append(
            "Faza początkowa stanowisk:"
        )

        for station_id, occupancy in candidate.station_initial_phase.items():
            lines.append(
                f"S{station_id}: {'ZAJĘTE' if occupancy else 'PUSTE'}"
            )
        lines.append(
            ""
        )

        lines.append(
            "Faza początkowa manipulatorów:"
        )

        for manipulator_id, value in getattr(
            candidate,
            "manipulator_initial_phase",
            {}
        ).items():

            if isinstance(
                value,
                (
                    list,
                    tuple
                )
            ):
                position = value[
                    0
                ]

                loaded = value[
                    1
                ] if len(
                    value
                ) > 1 else 0

            else:
                position = value
                loaded = 0

            lines.append(
                f"M{manipulator_id}: pozycja={position}, "
                f"{'ZAWIESZKA' if loaded else 'PUSTY'}"
            )
        if candidate.messages:
            lines.append(
                ""
            )

            lines.append(
                "Uwagi:"
            )

            for message in candidate.messages:
                lines.append(
                    f"- {message}"
                )

        return "\n".join(
            lines
        )
    def _initial_station_occupancy_for_program_simulation(
        self
    ):
        candidate = (
            self.last_cycle_candidate
        )

        if candidate is None:
            return None

        if (
            abs(
                self.cycle_start.value()
                -
                candidate.start_time
            )
            >
            0.001
            or
            abs(
                self.cycle_end.value()
                -
                candidate.end_time
            )
            >
            0.001
        ):
            return None

        return {
            station_id: occupancy
            for station_id, occupancy
            in candidate.station_initial_phase.items()
            if occupancy > 0
        }
    def _initial_manipulator_positions_for_program_simulation(
        self
    ):
        candidate = (
            self.last_cycle_candidate
        )

        if candidate is None:
            return None

        if (
            abs(
                self.cycle_start.value()
                -
                candidate.start_time
            )
            >
            0.001
            or
            abs(
                self.cycle_end.value()
                -
                candidate.end_time
            )
            >
            0.001
        ):
            return None

        phase = getattr(
            candidate,
            "manipulator_initial_phase",
            None
        )

        if not phase:
            return None

        result = {}

        for manipulator_id, value in phase.items():

            try:
                if (
                    isinstance(
                        value,
                        (
                            list,
                            tuple
                        )
                    )
                    and
                    len(
                        value
                    )
                    >=
                    1
                ):
                    position = int(
                        round(
                            float(
                                value[
                                    0
                                ]
                            )
                        )
                    )

                    loaded = int(
                        value[
                            1
                        ]
                    ) if len(
                        value
                    ) > 1 else 0

                else:
                    position = int(
                        round(
                            float(
                                value
                            )
                        )
                    )

                    loaded = 0

                if loaded != 0:
                    print(
                        f"PROGRAM INITIAL MANIPULATOR WARNING "
                        f"M{manipulator_id} starts loaded={loaded}. "
                        f"ProgramDriven currently assumes empty gripper."
                    )

                result[
                    int(
                        manipulator_id
                    )
                ] = (
                    position
                )

            except Exception:
                continue

        if not result:
            return None

        return result
    def find_closed_cycle(
        self
    ):
        if (
            self.result is None
            or
            self.configuration is None
        ):
            QMessageBox.warning(
                self,
                "Zamknięty cykl",
                "Najpierw uruchom symulację EventDriven."
            )
            return

        finder = MaterialCycleWindowFinder(
            configuration=(
                self.configuration
            ),
            result=(
                self.result
            ),
            max_program_words=(
                self.max_program_words.value()
            )
        )

        candidate = (
            finder.find_best(
                seed_start=(
                    self.cycle_start.value()
                ),
                seed_end=(
                    self.cycle_end.value()
                ),
                search_radius=1200.0,
                min_duration=120.0,
                max_duration=3600.0,
                time_step=10.0,
                duration_step=10.0
            )
        )

        if candidate is None:
            QMessageBox.warning(
                self,
                "Zamknięty cykl",
                "Nie znaleziono żadnego kandydata."
            )
            return

        self.last_cycle_candidate = (
            candidate
        )

        self.cycle_start.setValue(
            candidate.start_time
        )
        self.cycle_end.setValue(
            candidate.end_time
        )

        details = (
            self._format_candidate_details(
                candidate
            )
        )

        if candidate.valid:
            QMessageBox.information(
                self,
                "Znaleziono zamknięty cykl",
                details
            )

        else:
            QMessageBox.warning(
                self,
                "Nie znaleziono idealnego cyklu",
                (
                    "Ustawiono najlepszy znaleziony kandydat, "
                    "ale bilans, faza albo limit kroków nadal nie są idealne.\n\n"
                    +
                    details
                )
            )
