from math import inf

from src.core.program_driven_simulator import ProgramDrivenSimulator
from src.optimization.cycle_closure_validator import CycleClosureValidator
from src.optimization.event_driven_program_candidate_builder import (
    EventDrivenProgramCandidateBuilder
)
from src.optimization.optimization_runner import CandidateResult
from src.optimization.program_candidate_evaluator import ProgramCandidateEvaluator


class GeneratedProgramCandidateEvaluator:
    """Validate a newly generated PLC program against ProgramDriven."""

    VALID = "VALID"
    REJECTED = "REJECTED"

    def __init__(self, cycles=8, simulator_factory=None,
                 program_builder=None):
        self.cycles = max(2, int(cycles))
        self.simulator_factory = simulator_factory or ProgramDrivenSimulator
        self.program_builder = (
            program_builder or EventDrivenProgramCandidateBuilder(
                consult_cycles=max(2, min(4, self.cycles))
            )
        )
        self.closure_validator = CycleClosureValidator()

    @staticmethod
    def _initial_positions(build_result):
        return EventDrivenProgramCandidateBuilder._initial_positions(
            build_result.cycle, build_result.configuration
        )

    @staticmethod
    def _initial_occupancy(build_result):
        return EventDrivenProgramCandidateBuilder._initial_occupancy(
            build_result.cycle
        )

    @staticmethod
    def _final_positions(result, initial_positions):
        values = {int(mid): float(value)
                  for mid, value in initial_positions.items()}
        for segment in sorted(
            getattr(result, "timeline_segments", []),
            key=lambda item: (float(item.end_time), int(item.manipulator_id))
        ):
            values[int(segment.manipulator_id)] = float(segment.end_position)
        return tuple(values[mid] for mid in (1, 2, 3, 4))

    def _reasons(self, result, initial_positions, final_positions):
        reasons = []
        checks = (
            ("deadlocks", "PROGRAM_DEADLOCK"),
            ("process_violations", "PROGRAM_PROCESS_VIOLATION"),
            ("empty_pickup_warnings", "PROGRAM_EMPTY_PICKUP"),
            ("drop_without_hanger_warnings", "PROGRAM_DROP_WITHOUT_HANGER"),
            ("occupied_drop_warnings", "PROGRAM_OCCUPIED_DROP")
        )
        for field, code in checks:
            if getattr(result, field, []):
                reasons.append(code)
        compliance = list(getattr(result, "process_compliance", []))
        if any(
            not bool(getattr(item, "possible_min_ok", item.min_ok))
            for item in compliance
        ):
            reasons.append("PROGRAM_MIN_RESIDENCE")
        if any(
            not bool(getattr(item, "possible_max_ok", item.max_ok))
            for item in compliance
        ):
            reasons.append("PROGRAM_MAX_RESIDENCE")
        audit = getattr(result, "program_residence_audit", None)
        if audit is not None and not bool(audit.get("valid", False)):
            reasons.append("PROGRAM_RESIDENCE_AUDIT")
        track_events = getattr(result, "track_guard_events", [])
        if any(
            (item.get("mode") if isinstance(item, dict)
             else getattr(item, "mode", None)) == "warn"
            for item in track_events
        ):
            reasons.append("PROGRAM_TRACK_CONFLICT")
        closure = self.closure_validator.validate(
            tuple(initial_positions[mid] for mid in (1, 2, 3, 4)),
            final_positions,
            active_consults=getattr(result, "active_consults", None)
        )
        reasons.extend(f"PROGRAM_{item.code}" for item in closure)
        return tuple(dict.fromkeys(reasons))

    def __call__(self, event_candidate_result):
        build_result = self.program_builder.build(event_candidate_result)
        if not build_result.valid:
            return CandidateResult(
                candidate=event_candidate_result.candidate,
                status=self.REJECTED,
                objective=(inf, inf, inf, inf, inf, inf),
                metrics={
                    "evaluation_phase": "PROGRAM_BUILD",
                    "event_evaluation": event_candidate_result,
                    "program_build": build_result
                },
                rejection_reasons=tuple(
                    f"BUILD_{error}" for error in build_result.errors
                ) or ("BUILD_UNKNOWN_ERROR",)
            )

        initial_positions = self._initial_positions(build_result)
        initial_occupancy = self._initial_occupancy(build_result)
        simulator = self.simulator_factory(
            configuration=build_result.configuration,
            programs=build_result.programs,
            consults=build_result.consults,
            cycles=self.cycles,
            initial_station_occupancy=initial_occupancy,
            initial_manipulator_positions=initial_positions,
            initial_state_mode="cycle"
        )
        result = simulator.run()
        final_positions = self._final_positions(result, initial_positions)
        reasons = self._reasons(
            result, initial_positions, final_positions
        )
        cycle_time, throughput, hangers = (
            ProgramCandidateEvaluator._cycle_metrics(result)
        )
        event_throughput = float(event_candidate_result.metrics.get(
            "event_throughput_per_hour", 0.0
        ))
        realization_gap = event_throughput - throughput
        consult_wait = sum(
            ProgramCandidateEvaluator._consult_duration(item)
            for item in getattr(result, "consult_waits", [])
        )
        track_wait = sum(
            ProgramCandidateEvaluator._duration(item)
            for item in getattr(result, "track_waits", [])
        )
        process_idle = ProgramCandidateEvaluator._process_bath_idle_time(
            result, build_result.configuration
        )
        empty_travel = ProgramCandidateEvaluator._empty_travel_time(result)
        metrics = {
            "evaluation_phase": "PROGRAM_DRIVEN",
            "event_evaluation": event_candidate_result,
            "program_build": build_result,
            "program_cycle_time": cycle_time,
            "program_throughput_per_hour": throughput,
            "event_throughput_per_hour": event_throughput,
            "throughput_realization_gap": realization_gap,
            "throughput_realization_ratio": (
                throughput / event_throughput if event_throughput > 0 else 0.0
            ),
            "hangers_per_cycle": hangers,
            "gross_consult_wait": consult_wait,
            "track_wait": track_wait,
            "process_bath_idle_time": process_idle,
            "empty_travel_time": empty_travel,
            "initial_positions": tuple(
                initial_positions[mid] for mid in (1, 2, 3, 4)
            ),
            "final_positions": final_positions,
            "program_count": len(build_result.programs),
            "consult_count": len(build_result.consults),
            "result": result
        }
        objective = (
            cycle_time,
            process_idle,
            consult_wait,
            track_wait,
            empty_travel,
            -throughput
        )
        return CandidateResult(
            candidate=event_candidate_result.candidate,
            status=self.REJECTED if reasons else self.VALID,
            objective=objective,
            metrics=metrics,
            rejection_reasons=reasons
        )
