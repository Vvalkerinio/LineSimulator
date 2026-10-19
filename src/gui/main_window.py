from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QLabel,
    QFileDialog,
    QMessageBox
)

from src.gui.process_tab import (
    ProcessTab
)

from src.gui.manipulator_tab import (
    ManipulatorsTab
)

from src.gui.results_tab import (
    ResultsTab
)

from src.gui.simulation_tab import (
    SimulationTab
)

from src.gui.cyclogram_tab import (
    CyclogramTab
)

from src.gui.gantt_tab import (
    GanttTab
)

from src.gui.manipulator_trajectory_tab import (
    ManipulatorTrajectoryTab
)

from src.gui.line_overview_tab import (
    LineOverviewTab
)

from src.gui.reports_tab import (
    ReportsTab
)

from src.gui.optimization_tab import (
    OptimizationTab
)

from src.optimization.event_driven_optimization_factory import (
    EventDrivenOptimizationFactory
)

from src.io.configuration_serializer import (
    save_configuration,
    load_configuration,
    save_default_configuration,
    load_default_configuration
)


class MainWindow(QMainWindow):

    def __init__(
        self,
        configuration
    ):
        super().__init__()

        self.configuration = (
            configuration
        )

        self.current_config_path = None

        self.setWindowTitle(
            "Line Simulator v1.0"
        )

        self.resize(
            1400,
            900
        )

        self._create_menu()

        self._build_tabs()

    def _create_menu(
        self
    ):

        menu_bar = (
            self.menuBar()
        )

        file_menu = (
            menu_bar.addMenu(
                "Plik"
            )
        )

        load_action = (
            file_menu.addAction(
                "Wczytaj konfigurację..."
            )
        )

        load_action.triggered.connect(
            self.load_configuration_from_file
        )

        save_as_action = (
            file_menu.addAction(
                "Zapisz konfigurację jako..."
            )
        )

        save_as_action.triggered.connect(
            self.save_configuration_as
        )

        file_menu.addSeparator()

        save_default_action = (
            file_menu.addAction(
                "Zapisz jako domyślną"
            )
        )

        save_default_action.triggered.connect(
            self.save_as_default
        )

        load_default_action = (
            file_menu.addAction(
                "Wczytaj domyślną"
            )
        )

        load_default_action.triggered.connect(
            self.load_default
        )

    def _build_tabs(
        self
    ):

        tabs = QTabWidget()

        self.results_tab = (
            ResultsTab()
        )

        self.reports_tab = (
            ReportsTab()
        )

        self.cyclogram_tab = (
            CyclogramTab()
        )
        if hasattr(
            self.cyclogram_tab,
            "set_configuration"
        ):
            self.cyclogram_tab.set_configuration(
                self.configuration
            )

        self.gantt_tab = (
            GanttTab()
        )

        self.trajectory_tab = (
            ManipulatorTrajectoryTab(
                self.configuration
            )
        )

        self.line_overview_tab = (
            LineOverviewTab(
                self.configuration
            )
        )
        

        self.process_tab = (
            ProcessTab(
                self.configuration
            )
        )

        self.manipulator_tab = (
            ManipulatorsTab(
                self.configuration
            )
        )

        self.simulation_tab = (
            SimulationTab(
                self.configuration,
                self.results_tab,
                self.cyclogram_tab,
                self.gantt_tab,
                self.trajectory_tab,
                self.reports_tab
            )
        )
        self.simulation_tab.line_overview_tab = self.line_overview_tab
        self.optimization_tab = OptimizationTab(
            self.configuration
        )
        self.optimization_study_factory = EventDrivenOptimizationFactory(
            self.configuration,
            programs_provider=lambda: self.cyclogram_tab.programs,
            consults_provider=lambda: self.cyclogram_tab.consults
        )
        self.optimization_tab.set_factories(
            study_factory=self.optimization_study_factory.build,
            candidate_factory=self.optimization_study_factory.candidate_factory,
            prepare_callback=self._prepare_optimization,
            evaluate_candidate_callback=(
                self.optimization_study_factory.evaluate_candidate
            ),
            apply_result_callback=self._apply_optimization_result,
            restore_callback=self._restore_optimization_backup
        )

        if hasattr(
            self.cyclogram_tab,
            "set_output_tabs"
        ):
            self.cyclogram_tab.set_output_tabs(
                results_tab=(
                    self.results_tab
                ),
                gantt_tab=(
                    self.gantt_tab
                ),
                trajectory_tab=(
                    self.trajectory_tab
                ),
                reports_tab=(
                    self.reports_tab
                ),
                line_overview_tab=(
                    self.line_overview_tab
                )
            )

        tabs.addTab(
            self.process_tab,
            "Proces"
        )

        tabs.addTab(
            self.manipulator_tab,
            "Manipulatory"
        )

        tabs.addTab(
            self.simulation_tab,
            "Symulacja"
        )

        tabs.addTab(
            self.results_tab,
            "Wyniki"
        )

        tabs.addTab(
            self.reports_tab,
            "Raporty"
        )

        tabs.addTab(
            self.cyclogram_tab,
            "Cyklogram"
        )

        tabs.addTab(
            self.optimization_tab,
            "Optymalizacja"
        )

        tabs.addTab(
            self.gantt_tab,
            "Gantt"
        )

        tabs.addTab(
            self.trajectory_tab,
            "Trajektorie"
        )

        tabs.addTab(
            self.line_overview_tab,
            "Widok linii"
        )
        
        self.setCentralWidget(
            tabs
        )

    def _prepare_optimization(self):
        """Commit current GUI values before background optimization starts."""
        self._apply_editor_values()
        if hasattr(self.cyclogram_tab, "apply_program_table_changes"):
            self.cyclogram_tab.apply_program_table_changes(
                show_message=False
            )
        if hasattr(self.cyclogram_tab, "apply_consult_table_changes"):
            self.cyclogram_tab.apply_consult_table_changes(
                show_message=False
            )

    def _apply_optimization_result(self, result):
        """Apply a revalidated EventDriven configuration without changing PLC."""
        if result.status != "VALID":
            raise ValueError("Nie można zastosować odrzuconej konfiguracji.")
        import copy
        self._optimization_backup = {
            "positions": {
                int(item.id): int(item.position)
                for item in self.configuration.manipulators
            },
            "shared_bath": {
                int(station.id): (
                    getattr(station, "shared_bath_stagger_mode", "percent"),
                    float(getattr(station, "shared_bath_stagger_value", 50.0))
                )
                for station in self.configuration.stations
            }
        }
        positions = tuple(result.candidate.start_positions)
        for manipulator in self.configuration.manipulators:
            manipulator.position = int(positions[int(manipulator.id) - 1])
        by_group = {
            parameter.group_name: parameter
            for parameter in result.candidate.shared_bath_parameters
        }
        for station in self.configuration.stations:
            group = str(getattr(station, "shared_bath_group", "") or "")
            parameter = by_group.get(group)
            if parameter is None:
                continue
            station.shared_bath_stagger_mode = parameter.mode
            station.shared_bath_stagger_value = float(parameter.value)
        if hasattr(self.manipulator_tab, "_load_data"):
            self.manipulator_tab._load_data()
        if hasattr(self.process_tab, "_load_data"):
            self.process_tab._load_data()

    def _restore_optimization_backup(self):
        backup = getattr(self, "_optimization_backup", None)
        if not backup:
            return
        for manipulator in self.configuration.manipulators:
            manipulator.position = int(backup["positions"][int(manipulator.id)])
        for station in self.configuration.stations:
            mode, value = backup["shared_bath"][int(station.id)]
            station.shared_bath_stagger_mode = mode
            station.shared_bath_stagger_value = float(value)
        if hasattr(self.manipulator_tab, "_load_data"):
            self.manipulator_tab._load_data()
        if hasattr(self.process_tab, "_load_data"):
            self.process_tab._load_data()
        self._optimization_backup = None

    def _apply_editor_values(
        self
    ):

        if hasattr(
            self,
            "process_tab"
        ):
            self.process_tab.save_changes()

        from src.core.shared_bath_group_builder import (
            SharedBathGroupBuilder
        )

        self.configuration.shared_bath_groups = (
            SharedBathGroupBuilder()
            .build(
                self.configuration.stations
            )
        )

        if hasattr(
            self,
            "manipulator_tab"
        ):
            self.manipulator_tab.save_changes()

        if hasattr(
            self,
            "simulation_tab"
        ):

            tab = (
                self.simulation_tab
            )

            self.configuration.hanger_count = (
                tab.hanger_count.value()
            )

            self.configuration.entry_interval = (
                tab.entry_interval.value()
            )

            self.configuration.infinite_feed = (
                tab.infinite_feed.isChecked()
            )

            self.configuration.feed_duration = (
                tab.feed_duration.value()
            )

            self.configuration.warmup_time = (
                tab.warmup_time.value()
            )

            self.configuration.steady_state_window = (
                tab.steady_state_window.value()
            )

            if hasattr(
                tab,
                "minimum_manipulator_spacing"
            ):
                self.configuration.minimum_manipulator_spacing = (
                    tab.minimum_manipulator_spacing.value()
                )

            if hasattr(
                tab,
                "start_mode"
            ):
                from src.model.start_mode import (
                    StartMode
                )

                self.configuration.start_mode = (
                    StartMode.from_value(
                        tab.start_mode.currentData()
                    )
                )

        if hasattr(
            self,
            "cyclogram_tab"
        ):
            if hasattr(
                self.cyclogram_tab,
                "apply_to_configuration"
            ):
                self.cyclogram_tab.apply_to_configuration()

    def save_configuration_as(
        self
    ):

        self._apply_editor_values()

        path, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Zapisz konfigurację",
                "configs/config.json",
                "JSON files (*.json)"
            )
        )

        if not path:

            return

        save_configuration(
            self.configuration,
            path
        )

        self.current_config_path = (
            path
        )

        QMessageBox.information(
            self,
            "Konfiguracja",
            "Konfiguracja została zapisana."
        )

    def load_configuration_from_file(
        self
    ):

        path, _ = (
            QFileDialog.getOpenFileName(
                self,
                "Wczytaj konfigurację",
                "configs",
                "JSON files (*.json)"
            )
        )

        if not path:

            return

        self.configuration = (
            load_configuration(
                path
            )
        )

        self.current_config_path = (
            path
        )

        self._build_tabs()

        QMessageBox.information(
            self,
            "Konfiguracja",
            "Konfiguracja została wczytana."
        )

    def save_as_default(
        self
    ):

        self._apply_editor_values()

        save_default_configuration(
            self.configuration
        )

        QMessageBox.information(
            self,
            "Konfiguracja",
            "Konfiguracja została ustawiona jako domyślna."
        )

    def load_default(
        self
    ):

        self.configuration = (
            load_default_configuration()
        )

        self.current_config_path = None

        self._build_tabs()

        QMessageBox.information(
            self,
            "Konfiguracja",
            "Konfiguracja domyślna została wczytana."
        )
