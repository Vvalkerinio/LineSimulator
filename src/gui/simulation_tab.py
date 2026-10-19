from copy import deepcopy
import io
import sys
import traceback


from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QProgressBar,
    QApplication
)

from src.core.simulation_debug import debug_mode

from src.core.synchronized_output import (
    synchronized_redirect_stdout,
    usable_stdout
)

from src.core.event_driven_simulator import (
    EventDrivenSimulator
)

from src.core.simulation_services_factory import (
    SimulationServicesFactory
)

from src.analysis.kpi_engine import (
    KPIEngine
)

from src.model.start_mode import (
    StartMode
)


class TeeOutput:

    def __init__(self, *streams):
        self.streams = tuple(stream for stream in streams if stream is not None)

    def write(self, data):
        written = 0
        for stream in self.streams:
            try:
                if getattr(stream, "closed", False):
                    continue
                result = stream.write(data)
                if isinstance(result, int):
                    written = max(written, result)
            except (ValueError, OSError, AttributeError):
                continue
        return written

    def flush(self):
        for stream in self.streams:
            try:
                if getattr(stream, "closed", False):
                    continue
                stream.flush()
            except (ValueError, OSError, AttributeError):
                continue

    def isatty(self):
        return False


class SimulationTab(QWidget):

    def __init__(
        self,
        configuration,
        results_tab,
        cyclogram_tab,
        gantt_tab,
        trajectory_tab,
        reports_tab=None
    ):
        super().__init__()

        self.configuration = (
            configuration
        )
        self.results_tab = (
            results_tab
        )
        self.cyclogram_tab = (
            cyclogram_tab
        )
        self.gantt_tab = (
            gantt_tab
        )
        self.trajectory_tab = (
            trajectory_tab
        )
        self.reports_tab = (
            reports_tab
        )

        layout = QVBoxLayout()

        layout.addWidget(
            QLabel(
                "Liczba zawieszek"
            )
        )

        self.hanger_count = (
            QSpinBox()
        )
        self.hanger_count.setMinimum(
            1
        )
        self.hanger_count.setMaximum(
            100000
        )
        self.hanger_count.setValue(
            configuration.hanger_count
        )
        layout.addWidget(
            self.hanger_count
        )
        layout.addWidget(QLabel("Ilość sztuk na transport"))
        self.pieces_per_transport = QSpinBox()
        self.pieces_per_transport.setMinimum(1)
        self.pieces_per_transport.setMaximum(100000)
        self.pieces_per_transport.setValue(
            int(getattr(configuration, "pieces_per_transport", 7))
        )
        layout.addWidget(self.pieces_per_transport)
        layout.addWidget(
            self._build_predictive_pickup_controls()
        )

        layout.addWidget(
            QLabel(
                "Takt wejścia [s]"
            )
        )

        self.entry_interval = (
            QDoubleSpinBox()
        )
        self.entry_interval.setMinimum(
            1.0
        )
        self.entry_interval.setMaximum(
            3600.0
        )
        self.entry_interval.setValue(
            configuration.entry_interval
        )
        layout.addWidget(
            self.entry_interval
        )

        self.infinite_feed = (
            QCheckBox(
                "Infinite Feed"
            )
        )
        self.infinite_feed.setChecked(
            getattr(
                configuration,
                "infinite_feed",
                False
            )
        )
        layout.addWidget(
            self.infinite_feed
        )

        layout.addWidget(
            QLabel(
                "Feed Duration [s]"
            )
        )

        self.feed_duration = (
            QDoubleSpinBox()
        )
        self.feed_duration.setMinimum(
            60.0
        )
        self.feed_duration.setMaximum(
            86400.0
        )
        self.feed_duration.setValue(
            getattr(
                configuration,
                "feed_duration",
                3600.0
            )
        )
        layout.addWidget(
            self.feed_duration
        )

        layout.addWidget(
            QLabel(
                "Warmup Time [s]"
            )
        )

        self.warmup_time = (
            QDoubleSpinBox()
        )
        self.warmup_time.setMinimum(
            0.0
        )
        self.warmup_time.setMaximum(
            86400.0
        )
        self.warmup_time.setValue(
            getattr(
                configuration,
                "warmup_time",
                1800.0
            )
        )
        layout.addWidget(
            self.warmup_time
        )

        layout.addWidget(
            QLabel(
                "Steady State Window [s]"
            )
        )

        self.steady_state_window = (
            QDoubleSpinBox()
        )
        self.steady_state_window.setMinimum(
            60.0
        )
        self.steady_state_window.setMaximum(
            7200.0
        )
        self.steady_state_window.setValue(
            getattr(
                configuration,
                "steady_state_window",
                300.0
            )
        )
        layout.addWidget(
            self.steady_state_window
        )

        layout.addWidget(
            QLabel(
                "Minimalny odstęp manipulatorów [pozycje]"
            )
        )

        self.minimum_manipulator_spacing = (
            QDoubleSpinBox()
        )
        self.minimum_manipulator_spacing.setMinimum(
            0.0
        )
        self.minimum_manipulator_spacing.setMaximum(
            20.0
        )
        self.minimum_manipulator_spacing.setDecimals(
            1
        )
        self.minimum_manipulator_spacing.setSingleStep(
            0.5
        )
        self.minimum_manipulator_spacing.setValue(
            getattr(
                configuration,
                "minimum_manipulator_spacing",
                0.0
            )
        )
        layout.addWidget(
            self.minimum_manipulator_spacing
        )

        layout.addWidget(
            QLabel(
                "Start Mode"
            )
        )

        self.start_mode = (
            QComboBox()
        )

        self.start_mode.addItem(
            "Empty line",
            StartMode.EMPTY.value
        )

        self.start_mode.addItem(
            "Active baths prefilled",
            StartMode.ACTIVE_BATHS.value
        )

        current_start_mode = (
            StartMode.from_value(
                getattr(
                    configuration,
                    "start_mode",
                    StartMode.EMPTY
                )
            )
        )

        index = (
            self.start_mode.findData(
                current_start_mode.value
            )
        )

        if index >= 0:
            self.start_mode.setCurrentIndex(
                index
            )

        layout.addWidget(
            self.start_mode
        )
        layout.addWidget(
            QLabel(
                "Stan początkowy ProgramDriven"
            )
        )

        self.program_driven_initial_state = (
            QComboBox()
        )

        self.program_driven_initial_state.addItem(
            "Stan cyklu (prefill)",
            "cycle"
        )

        self.program_driven_initial_state.addItem(
            "Pusta linia",
            "empty"
        )

        current_program_initial_state = str(
            getattr(
                configuration,
                "program_driven_initial_state_mode",
                "cycle"
            )
        ).strip().lower()

        program_initial_state_index = (
            self.program_driven_initial_state.findData(
                current_program_initial_state
            )
        )

        if program_initial_state_index >= 0:
            self.program_driven_initial_state.setCurrentIndex(
                program_initial_state_index
            )

        layout.addWidget(
            self.program_driven_initial_state
        )

        program_initial_state_help = QLabel(
            "Stan cyklu odtwarza zajętość początku wykrytego cyklu. "
            "Pusta linia nie tworzy prefillu ani syntetycznych zawieszek. "
            "W tym trybie zawieszki mogą pojawić się wyłącznie na stanowisku "
            "załadunku."
        )

        program_initial_state_help.setWordWrap(
            True
        )

        layout.addWidget(
            program_initial_state_help
        )

        layout.addWidget(
            QLabel(
                "TrackGuard ProgramDriven"
            )
        )
        self.program_driven_track_guard_mode = QComboBox()
        self.program_driven_track_guard_mode.addItem(
            "OFF - sterowanie wyłącznie przez consulty",
            "off"
        )
        self.program_driven_track_guard_mode.addItem(
            "WARN - raportuj konflikty, nie blokuj ruchów",
            "warn"
        )
        self.program_driven_track_guard_mode.addItem(
            "ENFORCE - raportuj i przesuwaj ruchy",
            "enforce"
        )
        current_track_guard_mode = str(getattr(
            configuration,
            "program_driven_track_guard_mode",
            "off"
        )).strip().lower()
        track_guard_index = self.program_driven_track_guard_mode.findData(
            current_track_guard_mode
        )
        if track_guard_index < 0:
            track_guard_index = self.program_driven_track_guard_mode.findData(
                "off"
            )
        self.program_driven_track_guard_mode.setCurrentIndex(
            track_guard_index
        )
        layout.addWidget(
            self.program_driven_track_guard_mode
        )

        track_guard_help = QLabel(
            "OFF: TrackGuard nie wykrywa i nie blokuje ruchów. "
            "WARN: zapisuje konflikty z numerem INDEX PLC, ale nie zmienia trajektorii. "
            "ENFORCE: dodaje postoje i przesuwa ruchy. Domyślnie OFF, ponieważ consulty "
            "są mechanizmem synchronizacji programu PLC."
        )
        track_guard_help.setWordWrap(
            True
        )
        layout.addWidget(
            track_guard_help
        )

        self.debug_log = QCheckBox(
            "Debug log (spowalnia symulację)"
        )
        self.debug_log.setChecked(False)
        self.debug_log.setToolTip(
            "Włącza szczegółowe logi schedulera, Shared Bath, retry, pickup i YIELD."
        )
        layout.addWidget(self.debug_log)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Gotowe")
        layout.addWidget(self.progress_bar)
        self.progress_label = QLabel("Czas symulowany: 0.0 s | Zdarzenia: 0")
        layout.addWidget(self.progress_label)

        self.run_button = QPushButton(
            "Uruchom symulację"
        )
        self.run_button.clicked.connect(
            self.run_simulation
        )
        layout.addWidget(
            self.run_button
        )

        self.setLayout(
            layout
        )

    def _apply_values_to_configuration(
        self
    ):
        self.configuration.entry_interval = (
            self.entry_interval.value()
        )
        self.configuration.pieces_per_transport = (
            self.pieces_per_transport.value()
        )

        self.configuration.infinite_feed = (
            self.infinite_feed.isChecked()
        )

        self.configuration.feed_duration = (
            self.feed_duration.value()
        )

        self.configuration.warmup_time = (
            self.warmup_time.value()
        )

        self.configuration.steady_state_window = (
            self.steady_state_window.value()
        )

        self.configuration.minimum_manipulator_spacing = (
            self.minimum_manipulator_spacing.value()
        )

        self.configuration.start_mode = (
            StartMode.from_value(
                self.start_mode.currentData()
            )
        )
        self.configuration.program_driven_initial_state_mode = (
            self.program_driven_initial_state.currentData()
        )
        self.configuration.program_driven_track_guard_mode = (
            self.program_driven_track_guard_mode.currentData()
        )

        if (
            self.configuration.infinite_feed
        ):
            self.configuration.hanger_count = (
                self.configuration
                .effective_hanger_count()
            )

            self.hanger_count.setValue(
                self.configuration.hanger_count
            )

        else:
            self.configuration.hanger_count = (
                self.hanger_count.value()
            )
    def _parse_station_ids(
        self,
        text,
        default
    ):
        text = (
            str(
                text
            )
            .strip()
        )

        if not text:
            return list(
                default
            )

        result = []

        for part in text.split(
            ","
        ):
            part = (
                part
                .strip()
            )

            if not part:
                continue

            try:
                result.append(
                    int(
                        part
                    )
                )
            except ValueError:
                continue

        if not result:
            return list(
                default
            )

        return result
    def _build_predictive_pickup_controls(
        self
    ):
        group = QGroupBox(
            "Predictive pickup"
        )

        layout = QFormLayout()

        self.predictive_horizon_enabled = QCheckBox(
            "Włącz selektywny horizon"
        )

        self.predictive_horizon_enabled.setChecked(
            True
        )

        layout.addRow(
            self.predictive_horizon_enabled
        )

        self.predictive_horizon_time = QDoubleSpinBox()
        self.predictive_horizon_time.setMinimum(
            0.0
        )
        self.predictive_horizon_time.setMaximum(
            9999.0
        )
        self.predictive_horizon_time.setDecimals(
            1
        )
        self.predictive_horizon_time.setSingleStep(
            5.0
        )
        self.predictive_horizon_time.setValue(
            60.0
        )

        layout.addRow(
            "Horizon [s]",
            self.predictive_horizon_time
        )

        self.predictive_horizon_stations = QLineEdit(
            "19,20,21"
        )

        layout.addRow(
            "Stacje z horizon",
            self.predictive_horizon_stations
        )

        self.predictive_no_horizon_stations = QLineEdit(
            "3,4"
        )

        layout.addRow(
            "Stacje bez horizon",
            self.predictive_no_horizon_stations
        )

        group.setLayout(
            layout
        )

        return group
    def _apply_predictive_pickup_settings(
        self
    ):
        self.configuration.predictive_pickup_horizon_enabled = (
            self.predictive_horizon_enabled.isChecked()
        )

        self.configuration.predictive_pickup_horizon_time = (
            self.predictive_horizon_time.value()
        )

        self.configuration.predictive_pickup_horizon_station_ids = (
            self._parse_station_ids(
                self.predictive_horizon_stations.text(),
                default=[
                    19,
                    20,
                    21
                ]
            )
        )

        self.configuration.predictive_pickup_no_horizon_station_ids = (
            self._parse_station_ids(
                self.predictive_no_horizon_stations.text(),
                default=[
                    3,
                    4
                ]
            )
        )
    def _update_simulation_progress(
        self, percent, simulated_time, time_limit, event_count
    ):
        percent = max(0, min(100, int(percent)))
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"{percent}%")
        self.progress_label.setText(
            f"Czas symulowany: {simulated_time:.1f} / {time_limit:.1f} s | "
            f"Zdarzenia: {int(event_count)}"
        )
        QApplication.processEvents()

    def run_simulation(
        self
    ):
        buffer = io.StringIO()

        tee = TeeOutput(
            usable_stdout(),
            buffer
        )

        result = None

        with synchronized_redirect_stdout(tee):
            try:
                self._apply_values_to_configuration()

                # The simulator mutates manipulator.position as the run
                # advances. Never run on the editor configuration directly,
                # otherwise the final positions of the previous run become
                # the initial positions of the next run while the GUI still
                # displays the configured starting positions.
                simulation_configuration = deepcopy(self.configuration)
                services = (
                    SimulationServicesFactory.create(
                        simulation_configuration.manipulators,
                        simulation_configuration.stations
                    )
                )
                self._apply_predictive_pickup_settings()
                simulator = (
                    EventDrivenSimulator(
                        simulation_configuration,
                        services=services,
                        progress_callback=self._update_simulation_progress
                    )
                )

                with debug_mode(self.debug_log.isChecked()):
                    result = simulator.run()

                print(
                    f"Events: {len(result.events)}"
                )

                print(
                    f"Tasks: {len(result.manipulator_tasks)}"
                )

                print(
                    f"Deadlocks: "
                    f"{len(getattr(result, 'deadlocks', []))}"
                )

                print(
                    f"Violations: "
                    f"{len(getattr(result, 'process_violations', []))}"
                )

                print(
                    f"Generated hangers: "
                    f"{result.generated_hangers}"
                )

                print(
                    f"Minimum manipulator spacing: "
                    f"{self.configuration.minimum_manipulator_spacing}"
                )

                kpi = (
                    KPIEngine()
                    .calculate(
                        result,
                        simulation_configuration.pieces_per_transport
                    )
                )

                self.results_tab.show_results(
                    result,
                    kpi
                )

                if hasattr(
                    self.cyclogram_tab,
                    "update_result"
                ):
                    self.cyclogram_tab.update_result(
                        result,
                        self.configuration
                    )
                else:
                    self.cyclogram_tab.show_tasks(
                        result.manipulator_tasks
                    )

                self.gantt_tab.update_result(
                    result
                )

                self.trajectory_tab.update_result(
                    result
                )

                if hasattr(self, "line_overview_tab"):
                    self.line_overview_tab.update_result(
                        result
                    )

            except Exception:
                error_text = (
                    "\n" + "=" * 60 +
                    "\nSIMULATION ERROR\n" +
                    "=" * 60 + "\n" +
                    traceback.format_exc() + "\n"
                )
                buffer.write(error_text)
                console = usable_stdout()
                try:
                    console.write(error_text)
                    console.flush()
                except (ValueError, OSError, AttributeError):
                    pass

        if (
            self.reports_tab
            is not None
        ):
            self.reports_tab.show_report_text(
                buffer.getvalue()
            )