from collections import Counter
from math import inf

from src.core.synchronized_output import synchronized_suppress_stdout

from src.analysis.kpi_engine import KPIEngine
from src.analysis.event_throughput_analyzer import EventThroughputAnalyzer
from src.core.event_driven_simulator import EventDrivenSimulator
from src.optimization.event_driven_candidate_applier import (
    EventDrivenCandidateApplier
)
from src.optimization.optimization_runner import CandidateResult


class EventDrivenCandidateEvaluator:
    """Screen one EventDriven candidate before any PLC program is generated."""

    VALID = "VALID"
    REJECTED = "REJECTED"

    def __init__(self, configuration, simulator_factory=None,
                 candidate_applier=None, kpi_engine=None):
        self.base_configuration = configuration
        self.simulator_factory = simulator_factory or EventDrivenSimulator
        self.candidate_applier = candidate_applier or EventDrivenCandidateApplier()
        self.kpi_engine = kpi_engine or KPIEngine()

    @staticmethod
    def _deduplicate(values):
        return tuple(dict.fromkeys(values))

    @staticmethod
    def _shared_bath_usage(result, configuration):
        station_to_group = {
            int(station.id): str(station.shared_bath_group)
            for station in configuration.stations
            if getattr(station, "shared_bath_group", None)
        }
        counts = Counter()
        for event in getattr(result, "events", []):
            target = getattr(event, "target_station", None)
            if target is None or int(target) not in station_to_group:
                continue
            event_type = str(getattr(
                getattr(event, "event_type", ""), "name",
                getattr(event, "event_type", "")
            )).upper()
            # EventDriven records a completed physical placement as
            # TRANSPORT_END at the selected target station.
            if event_type != "TRANSPORT_END":
                continue
            counts[(station_to_group[int(target)], int(target))] += 1
        grouped = {}
        for (group, station_id), count in sorted(counts.items()):
            grouped.setdefault(group, {})[station_id] = count
        return grouped

    @staticmethod
    def _compliance_counts(result):
        records = list(getattr(result, "process_compliance", []))
        min_failures = sum(1 for item in records if not bool(item.min_ok))
        max_failures = sum(1 for item in records if not bool(item.max_ok))
        hard_min_failures = sum(
            1 for item in records
            if not bool(getattr(item, "possible_min_ok", item.min_ok))
        )
        hard_max_failures = sum(
            1 for item in records
            if not bool(getattr(item, "possible_max_ok", item.max_ok))
        )
        tradeoff_count = sum(
            1 for item in records
            if str(getattr(item, "compliance_status", ""))
            in ("TRADEOFF_MIN", "TRADEOFF_MAX")
        )
        total_deviation = sum(
            float(getattr(item, "nominal_deviation", 0.0))
            for item in records
        )
        max_deviation = max(
            [float(getattr(item, "nominal_deviation", 0.0)) for item in records]
            or [0.0]
        )
        return (
            records, min_failures, max_failures,
            hard_min_failures, hard_max_failures,
            tradeoff_count, total_deviation, max_deviation
        )

    @staticmethod
    def _steady_state_metrics(result):
        steady = getattr(result, "steady_state", None) or {}
        return {
            "steady_state_detected": bool(steady.get("detected", False)),
            "steady_state_throughput": float(steady.get(
                "throughput", steady.get("mean_throughput", 0.0)
            ) or 0.0),
            "steady_state_reason": str(steady.get("reason", "")),
            "steady_state_time": steady.get("steady_state_time")
        }

    def _rejection_reasons(self, result, kpi, steady=None):
        reasons = []
        steady = steady or self._steady_state_metrics(result)
        (
            records, min_failures, max_failures,
            hard_min_failures, hard_max_failures,
            tradeoff_count, total_nominal_deviation, max_nominal_deviation
        ) = self._compliance_counts(result)
        if getattr(result, "deadlocks", []):
            reasons.append("EVENT_DEADLOCK")
        if getattr(result, "process_violations", []):
            reasons.append("EVENT_PROCESS_VIOLATION")
        if hard_min_failures:
            reasons.append("EVENT_MIN_RESIDENCE")
        if hard_max_failures:
            reasons.append("EVENT_MAX_RESIDENCE")
        if int(getattr(result, "processed_events", 0)) <= 0:
            reasons.append("EVENT_NO_EVENTS")
        effective_throughput = max(
            float(getattr(kpi, "transports_per_hour", 0.0)),
            float(steady.get("steady_state_throughput", 0.0))
        )
        if (
            int(getattr(result, "completed_transports", 0)) <= 0
            and effective_throughput <= 0.0
        ):
            reasons.append("EVENT_NO_COMPLETED_TRANSPORT")
        if effective_throughput <= 0.0:
            reasons.append("EVENT_ZERO_THROUGHPUT")
        return self._deduplicate(reasons)

    def __call__(self, candidate):
        try:
            configuration = self.candidate_applier.apply(
                self.base_configuration, candidate
            )
        except Exception as exc:
            return CandidateResult(
                candidate=candidate,
                status=self.REJECTED,
                objective=(inf, inf, inf, inf, inf),
                metrics={
                    "evaluation_phase": "EVENT_APPLY",
                    "exception": f"{type(exc).__name__}: {exc}"
                },
                rejection_reasons=("EVENT_INVALID_CANDIDATE",)
            )

        simulator = self.simulator_factory(configuration)
        with synchronized_suppress_stdout():
            result = simulator.run()
        kpi = self.kpi_engine.calculate(result)
        (
            records, min_failures, max_failures,
            hard_min_failures, hard_max_failures,
            tradeoff_count, total_nominal_deviation, max_nominal_deviation
        ) = self._compliance_counts(result)
        steady = self._steady_state_metrics(result)
        steady_raw = getattr(result, "steady_state", None) or {}
        analysis_start = steady_raw.get(
            "analysis_start", steady.get("steady_state_time") or 0.0
        )
        analysis_end = steady_raw.get(
            "analysis_end", getattr(result, "final_time", 0.0)
        )
        throughput_analysis = EventThroughputAnalyzer().analyze(
            result, analysis_start, analysis_end
        )
        throughput = float(kpi.transports_per_hour)
        # Inter-exit estimator is continuous and avoids window-count steps.
        # Fall back to the established steady-state window estimator when fewer
        # than two exits are available.
        interval_throughput = float(
            throughput_analysis["interval_rate_per_hour"]
        )
        event_throughput = (
            interval_throughput
            or steady["steady_state_throughput"]
            or throughput
        )
        effective_steady = dict(steady)
        effective_steady["steady_state_throughput"] = event_throughput
        reasons = self._rejection_reasons(result, kpi, effective_steady)
        deadlock_count = len(getattr(result, "deadlocks", []))
        violation_count = len(getattr(result, "process_violations", []))
        final_time = float(getattr(result, "final_time", 0.0))
        metrics = {
            "evaluation_phase": "EVENT_DRIVEN",
            "event_final_time": final_time,
            "event_processed_events": int(result.processed_events),
            "event_scheduled_transports": int(result.scheduled_transports),
            "event_completed_transports": int(result.completed_transports),
            "event_throughput_per_hour": event_throughput,
            "window_throughput_per_hour": throughput,
            "windowed_steady_throughput_per_hour": float(
                steady["steady_state_throughput"]
            ),
            "interval_throughput_per_hour": interval_throughput,
            "throughput_exit_count": int(throughput_analysis["exit_count"]),
            "throughput_analysis_duration": float(
                throughput_analysis["analysis_duration"]
            ),
            "mean_exit_interval": throughput_analysis["mean_exit_interval"],
            "exit_interval_cv": float(
                throughput_analysis["exit_interval_cv"]
            ),
            "event_deadlock_count": deadlock_count,
            "event_watchdog_triggered": bool(getattr(
                result, "event_watchdog_triggered", False
            )),
            "shared_bath_retry_limit_reached": bool(getattr(
                result, "shared_bath_retry_limit_reached", False
            )),
            "event_process_violation_count": violation_count,
            "event_min_residence_failures": min_failures,
            "event_max_residence_failures": max_failures,
            "event_hard_min_residence_failures": hard_min_failures,
            "event_hard_max_residence_failures": hard_max_failures,
            "event_process_tradeoff_count": tradeoff_count,
            "event_total_nominal_deviation": total_nominal_deviation,
            "event_max_nominal_deviation": max_nominal_deviation,
            "event_compliance_record_count": len(records),
            "shared_bath_usage": self._shared_bath_usage(
                result, configuration
            ),
            "shared_bath_parameters": tuple(
                (item.group_name, item.mode, item.value)
                for item in candidate.shared_bath_parameters
            ),
            "start_positions": tuple(candidate.start_positions),
            "configuration": configuration,
            "result": result,
            **steady
        }
        # Validity always dominates ranking. Among valid EventDriven candidates,
        # maximize throughput then prefer fewer moves/events and shorter horizon.
        objective = (
            hard_min_failures + hard_max_failures + violation_count + deadlock_count,
            -event_throughput,
            tradeoff_count,
            total_nominal_deviation,
            max_nominal_deviation,
            -int(result.completed_transports),
            int(result.processed_events),
            final_time
        )
        return CandidateResult(
            candidate=candidate,
            status=self.REJECTED if reasons else self.VALID,
            objective=objective,
            metrics=metrics,
            rejection_reasons=reasons
        )
