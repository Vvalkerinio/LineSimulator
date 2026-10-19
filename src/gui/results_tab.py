from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QGroupBox, QTextEdit
)


class ResultsTab(QWidget):
    """Compact production KPI panel plus the former detailed metrics."""

    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout()

        kpi_group = QGroupBox("KPI")
        kpi_layout = QFormLayout()
        self.parts_per_hour = QLabel("-")
        self.transports_per_hour = QLabel("-")
        self.cycle_time = QLabel("-")
        self.process_violations_count = QLabel("-")
        self.manipulator_separation = QLabel("-")
        kpi_layout.addRow("Precise Event Throughput - Ilość szt/h", self.parts_per_hour)
        kpi_layout.addRow("Precise Event Throughput - Ilość transportów/h", self.transports_per_hour)
        kpi_layout.addRow("Cycle Time [s]", self.cycle_time)
        kpi_layout.addRow("Process Violations", self.process_violations_count)
        kpi_layout.addRow("Manipulator Separation", self.manipulator_separation)
        kpi_group.setLayout(kpi_layout)

        details_group = QGroupBox("Szczegóły symulacji")
        details_layout = QFormLayout()
        detail_specs = [
            ("simulation_time", "Simulation Time"),
            ("processed_events", "Processed Events"),
            ("generated_hangers", "Generated Hangers"),
            ("scheduled_transports", "Scheduled Transports"),
            ("completed_transports", "Completed Transports"),
            ("total_process_time", "Total Process Time"),
            ("deadlocks_count", "Deadlocks"),
            ("program_cycle_time", "Program Cycle Time"),
            ("program_hangers_per_cycle", "Program Hangers / Cycle"),
            ("steady_state", "Steady State"),
            ("steady_state_time", "Steady State From"),
            ("steady_state_throughput", "Steady State Throughput"),
            ("steady_state_reason", "Steady State Reason"),
            ("analysis_range", "Analysis Range"),
            ("mean_throughput", "Mean Throughput"),
            ("std_throughput", "Std Throughput"),
            ("cv_throughput", "CV Throughput"),
            ("interval_throughput", "Interval Throughput"),
            ("mean_exit_interval", "Mean Exit Interval"),
            ("throughput_exit_count", "Throughput Exit Count"),
            ("exit_interval_cv", "Exit Interval CV"),
        ]
        for attribute, title in detail_specs:
            label = QLabel("-")
            setattr(self, attribute, label)
            details_layout.addRow(title, label)
        details_group.setLayout(details_layout)

        warnings_group = QGroupBox("Warnings")
        warnings_layout = QVBoxLayout()
        self.warning_list = QTextEdit()
        self.warning_list.setReadOnly(True)
        warnings_layout.addWidget(self.warning_list)
        warnings_group.setLayout(warnings_layout)

        main_layout.addWidget(kpi_group)
        main_layout.addWidget(details_group)
        main_layout.addWidget(warnings_group)
        self.setLayout(main_layout)

    @staticmethod
    def _fmt(value, digits=2, suffix=""):
        if value is None:
            return "-"
        return f"{float(value):.{digits}f}{suffix}"

    def _show_steady_state(self, result):
        steady = getattr(result, "steady_state", None) or {}
        self.steady_state.setText("YES" if steady.get("detected", False) else "NO")
        self.steady_state_time.setText(self._fmt(steady.get("steady_state_time"), 0, " s"))
        self.steady_state_throughput.setText(self._fmt(steady.get("throughput"), 2, " transportów/h"))
        self.steady_state_reason.setText(str(steady.get("reason", "-")))
        start, end = steady.get("analysis_start"), steady.get("analysis_end")
        self.analysis_range.setText(
            f"{float(start):.0f} - {float(end):.0f} s"
            if start is not None and end is not None else "-"
        )
        self.mean_throughput.setText(self._fmt(steady.get("mean_throughput")))
        self.std_throughput.setText(self._fmt(steady.get("std_throughput")))
        self.cv_throughput.setText(self._fmt(steady.get("coefficient_of_variation"), 4))
        self.interval_throughput.setText(self._fmt(steady.get("interval_throughput")))
        self.mean_exit_interval.setText(self._fmt(steady.get("mean_exit_interval"), 2, " s"))
        self.throughput_exit_count.setText(str(steady.get("throughput_exit_count", "-")))
        self.exit_interval_cv.setText(self._fmt(steady.get("exit_interval_cv"), 4))

    def show_results(self, simulation_result, kpi):
        self.parts_per_hour.setText(f"{kpi.parts_per_hour:.2f}")
        self.transports_per_hour.setText(f"{kpi.transports_per_hour:.2f}")
        self.cycle_time.setText(
            "-" if kpi.average_cycle_time is None
            else f"{kpi.average_cycle_time:.2f}"
        )
        violations = len(getattr(simulation_result, "process_violations", []))
        # Compliance hard failures may be recorded independently of legacy violations.
        hard_compliance = sum(
            1 for item in getattr(simulation_result, "process_compliance", [])
            if str(getattr(item, "compliance_status", ""))
            in ("HARD_MIN_VIOLATION", "HARD_MAX_VIOLATION")
        )
        self.process_violations_count.setText(str(max(violations, hard_compliance)))
        unsafe = bool(
            getattr(simulation_result, "event_track_safety_violation", False)
        )
        for deadlock in getattr(simulation_result, "deadlocks", []):
            if isinstance(deadlock, dict):
                deadlock_type = deadlock.get("type")
                hanger_id = deadlock.get("hanger_id")
            else:
                deadlock_type = getattr(deadlock, "type", None)
                hanger_id = getattr(
                deadlock,
                "hanger_id",
                None
            )
            if deadlock_type == "EVENT_TRACK_SAFETY_INVARIANT_BROKEN":
                unsafe = True
                break
        _ = hanger_id if 'hanger_id' in locals() else None
        self.manipulator_separation.setText("NOK" if unsafe else "OK")

        self.simulation_time.setText(f"{simulation_result.final_time:.2f}")
        self.processed_events.setText(str(simulation_result.processed_events))
        self.generated_hangers.setText(str(simulation_result.generated_hangers))
        self.scheduled_transports.setText(str(simulation_result.scheduled_transports))
        self.completed_transports.setText(str(simulation_result.completed_transports))
        self.total_process_time.setText(f"{simulation_result.total_process_time:.2f}")
        self.deadlocks_count.setText(str(len(getattr(simulation_result, "deadlocks", []))))
        program = getattr(simulation_result, "program_cycle_kpi", None)
        if program:
            self.program_cycle_time.setText(self._fmt(program.get("cycle_duration"), 2, " s"))
            self.program_hangers_per_cycle.setText(self._fmt(program.get("hangers_per_cycle")))
        else:
            self.program_cycle_time.setText("-")
            self.program_hangers_per_cycle.setText("-")
        self._show_steady_state(simulation_result)
        warnings = getattr(simulation_result, "warnings", [])
        self.warning_list.setPlainText("\n".join(map(str, warnings)) if warnings else "")
