from math import inf

from src.core.program_driven_simulator import ProgramDrivenSimulator
from src.optimization.configuration_clone import clone_configuration_for_candidate
from src.optimization.cycle_closure_validator import CycleClosureValidator
from src.optimization.optimization_runner import CandidateResult


class ProgramCandidateEvaluator:
    """Evaluate one candidate against the current PLC program and consults.

    This stage deliberately keeps the process, PLC words and consult graph
    unchanged. It varies only initial positions and evaluates the resulting
    ProgramDriven execution. Program regeneration is a later pipeline stage.
    """

    VALID = "VALID"
    REJECTED = "REJECTED"

    def __init__(self, configuration, programs, consults=None, cycles=4,
                 initial_state_mode="cycle", simulator_factory=None,
                 transformer=None):
        self.base_configuration = configuration
        self.programs = programs
        self.consults = list(consults or [])
        self.cycles = max(2, int(cycles))
        self.initial_state_mode = initial_state_mode
        self.simulator_factory = simulator_factory or ProgramDrivenSimulator
        self.cycle_closure_validator = CycleClosureValidator()
        self.transformer = transformer

    @staticmethod
    def _positions_dict(candidate):
        return {
            manipulator_id: candidate.start_positions[manipulator_id - 1]
            for manipulator_id in (1, 2, 3, 4)
        }

    @staticmethod
    def _final_positions(result, start_positions):
        final_positions = {
            manipulator_id: float(start_positions[manipulator_id - 1])
            for manipulator_id in (1, 2, 3, 4)
        }
        segments = sorted(
            getattr(result, "timeline_segments", []),
            key=lambda item: (float(item.end_time), int(item.manipulator_id))
        )
        for segment in segments:
            final_positions[int(segment.manipulator_id)] = float(
                segment.end_position
            )
        return tuple(final_positions[mid] for mid in (1, 2, 3, 4))

    @staticmethod
    def _duration(item):
        if isinstance(item, dict):
            start = item.get("start_time", item.get("start", 0.0))
            end = item.get("end_time", item.get("end", start))
        else:
            start = getattr(item, "start_time", getattr(item, "start", 0.0))
            end = getattr(item, "end_time", getattr(item, "end", start))
        return max(0.0, float(end) - float(start))

    @staticmethod
    def _consult_duration(item):
        if isinstance(item, dict):
            if "duration" in item:
                return max(0.0, float(item["duration"]))
        elif hasattr(item, "duration"):
            return max(0.0, float(item.duration))
        return ProgramCandidateEvaluator._duration(item)

    @staticmethod
    def _process_bath_idle_time(result, configuration):
        process_ids = {
            int(station.id)
            for station in getattr(configuration, "stations", [])
            if bool(getattr(station, "is_process_bath", True))
        }
        total = 0.0
        for segment in getattr(result, "timeline_segments", []):
            if getattr(segment, "segment_type", "") != "idle":
                continue
            position = int(round(float(segment.start_position)))
            if position in process_ids:
                total += ProgramCandidateEvaluator._duration(segment)
        return total

    @staticmethod
    def _empty_travel_time(result):
        return sum(
            ProgramCandidateEvaluator._duration(segment)
            for segment in getattr(result, "timeline_segments", [])
            if getattr(segment, "segment_type", "") == "empty_move"
        )

    @staticmethod
    def _cycle_metrics(result):
        kpi = getattr(result, "program_cycle_kpi", None) or {}
        if not isinstance(kpi, dict):
            return inf, 0.0, 0.0
        cycle_time = float(kpi.get(
            "cycle_duration",
            kpi.get(
                "program_cycle_time",
                kpi.get("average_cycle_duration", inf)
            )
        ))
        throughput = float(kpi.get(
            "throughput",
            kpi.get("throughput_per_hour", 0.0)
        ))
        hangers = float(kpi.get(
            "hangers_per_cycle",
            kpi.get("hangers_per_program_cycle", 0.0)
        ))
        return cycle_time, throughput, hangers

    def _rejection_reasons(self, result, candidate, final_positions):
        reasons = []
        if getattr(result, "deadlocks", []):
            reasons.append("DEADLOCK")
        if getattr(result, "process_violations", []):
            reasons.append("PROCESS_VIOLATION")
        compliance = list(getattr(result, "process_compliance", []))
        if any(
            not bool(getattr(record, "possible_min_ok", record.min_ok))
            for record in compliance
        ):
            reasons.append("MIN_RESIDENCE")
        if any(
            not bool(getattr(record, "possible_max_ok", record.max_ok))
            for record in compliance
        ):
            reasons.append("MAX_RESIDENCE")
        audit = getattr(result, "program_residence_audit", None)
        if audit is not None and not bool(audit.get("valid", False)):
            reasons.append("RESIDENCE_AUDIT")
        warning_fields = (
            ("empty_pickup_warnings", "EMPTY_PICKUP"),
            ("drop_without_hanger_warnings", "DROP_WITHOUT_HANGER"),
            ("occupied_drop_warnings", "OCCUPIED_DROP")
        )
        for field, code in warning_fields:
            if getattr(result, field, []):
                reasons.append(code)
        track_events = getattr(result, "track_guard_events", [])
        if any(
            (item.get("mode") if isinstance(item, dict)
             else getattr(item, "mode", None)) == "warn"
            for item in track_events
        ):
            reasons.append("TRACK_CONFLICT")
        closure = self.cycle_closure_validator.validate(
            candidate.start_positions,
            final_positions,
            active_consults=getattr(result, "active_consults", None)
        )
        reasons.extend(item.code for item in closure)
        return tuple(dict.fromkeys(reasons))

    def __call__(self, candidate):
        configuration = clone_configuration_for_candidate(
            self.base_configuration
        )
        by_id = {
            int(item.id): item
            for item in getattr(configuration, "manipulators", [])
        }
        for manipulator_id, position in self._positions_dict(candidate).items():
            by_id[manipulator_id].position = int(position)

        programs = self.programs
        consults = self.consults
        transformation = None
        if self.transformer is not None:
            transformation = self.transformer.transform(
                programs, consults, candidate
            )
            if not transformation.valid:
                return CandidateResult(
                    candidate=candidate,
                    status=self.REJECTED,
                    objective=(inf, inf, inf, inf, inf, 0.0),
                    metrics={"transformation": transformation},
                    rejection_reasons=tuple(transformation.errors)
                )
            programs = transformation.programs
            consults = transformation.consults

        simulator = self.simulator_factory(
            configuration=configuration,
            programs=programs,
            consults=consults,
            cycles=self.cycles,
            initial_manipulator_positions=self._positions_dict(candidate),
            initial_state_mode=self.initial_state_mode
        )
        result = simulator.run()
        final_positions = self._final_positions(
            result,
            candidate.start_positions
        )
        reasons = self._rejection_reasons(
            result,
            candidate,
            final_positions
        )
        cycle_time, throughput, hangers = self._cycle_metrics(result)
        gross_consult_wait = sum(
            self._consult_duration(item)
            for item in getattr(result, "consult_waits", [])
        )
        track_wait = sum(
            self._duration(item)
            for item in getattr(result, "track_waits", [])
        )
        process_bath_idle = self._process_bath_idle_time(
            result,
            configuration
        )
        empty_travel = self._empty_travel_time(result)
        metrics = {
            "program_cycle_time": cycle_time,
            "throughput_per_hour": throughput,
            "hangers_per_cycle": hangers,
            "gross_consult_wait": gross_consult_wait,
            "track_wait": track_wait,
            "process_bath_idle_time": process_bath_idle,
            "empty_travel_time": empty_travel,
            "start_positions": tuple(candidate.start_positions),
            "final_positions": tuple(final_positions),
            "residence_record_count": len(
                getattr(result, "process_compliance", [])
            ),
            "result": result,
            "transformation": transformation
        }
        objective = (
            cycle_time,
            process_bath_idle,
            gross_consult_wait,
            track_wait,
            empty_travel,
            -throughput
        )
        return CandidateResult(
            candidate=candidate,
            status=self.REJECTED if reasons else self.VALID,
            objective=objective,
            metrics=metrics,
            rejection_reasons=reasons
        )
