from dataclasses import dataclass, field

from src.analysis.consult_pipeline import ConsultPipeline
from src.analysis.manipulator_program_builder import ManipulatorProgramBuilder
from src.analysis.material_cycle_window_finder import MaterialCycleWindowFinder


@dataclass
class EventDrivenProgramBuildResult:
    valid: bool
    candidate: object
    cycle: object = None
    programs: dict = field(default_factory=dict)
    consults: list = field(default_factory=list)
    configuration: object = None
    event_result: object = None
    consult_resolution: object = None
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class EventDrivenProgramCandidateBuilder:
    """Create a complete PLC program and fresh consults from EventDriven output."""

    def __init__(self, max_program_words=99, station_id_shift=1,
                 consult_cycles=4, max_consult_iterations=40,
                 cycle_finder_factory=None, program_builder_factory=None,
                 consult_pipeline_factory=None):
        self.max_program_words = int(max_program_words)
        self.station_id_shift = int(station_id_shift)
        self.consult_cycles = max(2, int(consult_cycles))
        self.max_consult_iterations = max(1, int(max_consult_iterations))
        self.cycle_finder_factory = (
            cycle_finder_factory or MaterialCycleWindowFinder
        )
        self.program_builder_factory = (
            program_builder_factory or ManipulatorProgramBuilder
        )
        self.consult_pipeline_factory = consult_pipeline_factory or ConsultPipeline

    @staticmethod
    def _seed_window(event_result):
        final_time = float(getattr(event_result, "final_time", 0.0))
        steady = getattr(event_result, "steady_state", None) or {}
        start = steady.get("analysis_start", steady.get("steady_state_time"))
        end = steady.get("analysis_end")
        if start is None:
            start = max(0.0, final_time * 0.5)
        if end is None:
            end = final_time
        start, end = float(start), float(end)
        if end <= start:
            start = max(0.0, final_time - min(1800.0, final_time))
            end = final_time
        return start, end

    @staticmethod
    def _initial_positions(cycle, configuration):
        phase = getattr(cycle, "manipulator_initial_phase", {}) or {}
        result = {}
        for manipulator in configuration.manipulators:
            value = phase.get(int(manipulator.id), manipulator.position)
            if isinstance(value, (tuple, list)):
                value = value[0]
            result[int(manipulator.id)] = int(round(float(value)))
        return result

    @staticmethod
    def _initial_occupancy(cycle):
        phase = getattr(cycle, "station_initial_phase", {}) or {}
        occupancy = {}
        for station_id, value in phase.items():
            if isinstance(value, (tuple, list)):
                value = value[0] if value else 0
            occupancy[int(station_id)] = int(value)
        return occupancy or None

    @staticmethod
    def _program_errors(programs):
        errors = []
        if set(int(mid) for mid in programs) != {1, 2, 3, 4}:
            errors.append("PROGRAM_MISSING_MANIPULATOR")
        for manipulator_id, program in sorted(programs.items()):
            if not getattr(program, "steps", []):
                errors.append(f"PROGRAM_EMPTY_M{manipulator_id}")
            raw_words = len(getattr(program, "steps", [])) * 3
            if raw_words > int(getattr(program, "max_program_words", 99)):
                errors.append(
                    f"PROGRAM_WORD_LIMIT_M{manipulator_id}:{raw_words}"
                )
        return errors

    def build(self, event_candidate_result):
        candidate = event_candidate_result.candidate
        if event_candidate_result.status != "VALID":
            return EventDrivenProgramBuildResult(
                valid=False,
                candidate=candidate,
                errors=["EVENT_CANDIDATE_NOT_VALID"]
            )
        configuration = event_candidate_result.metrics.get("configuration")
        event_result = event_candidate_result.metrics.get("result")
        if configuration is None or event_result is None:
            return EventDrivenProgramBuildResult(
                valid=False,
                candidate=candidate,
                errors=["EVENT_RESULT_CONTEXT_MISSING"]
            )

        seed_start, seed_end = self._seed_window(event_result)
        finder = self.cycle_finder_factory(
            configuration=configuration,
            result=event_result,
            max_program_words=self.max_program_words
        )
        cycle = finder.find_best(seed_start=seed_start, seed_end=seed_end)
        if cycle is None:
            return EventDrivenProgramBuildResult(
                valid=False, candidate=candidate,
                configuration=configuration, event_result=event_result,
                errors=["EVENT_NO_CYCLE_CANDIDATE"]
            )
        if not bool(getattr(cycle, "valid", False)):
            messages = list(getattr(cycle, "messages", []))
            return EventDrivenProgramBuildResult(
                valid=False, candidate=candidate, cycle=cycle,
                configuration=configuration, event_result=event_result,
                errors=["EVENT_NO_VALID_CLOSED_CYCLE"], notes=messages
            )

        index_addresses = dict(getattr(
            configuration, "program_index_addresses", {}
        ) or {1: 500, 2: 600, 3: 700, 4: 800})
        station_offsets = dict(getattr(
            configuration, "program_station_offsets", {}
        ) or {1: 0, 2: 0, 3: 0, 4: 0})
        builder = self.program_builder_factory(
            configuration=configuration,
            result=event_result,
            cycle_start_time=float(cycle.start_time),
            cycle_end_time=float(cycle.end_time),
            index_addresses_by_manipulator=index_addresses,
            station_offsets_by_manipulator=station_offsets,
            station_id_shift=self.station_id_shift,
            max_program_words=self.max_program_words
        )
        programs = builder.build()
        errors = self._program_errors(programs)
        if errors:
            return EventDrivenProgramBuildResult(
                valid=False, candidate=candidate, cycle=cycle,
                programs=programs, configuration=configuration,
                event_result=event_result, errors=errors
            )

        initial_positions = self._initial_positions(cycle, configuration)
        initial_occupancy = self._initial_occupancy(cycle)
        pipeline = self.consult_pipeline_factory(
            configuration=configuration,
            programs=programs,
            cycles=self.consult_cycles,
            initial_station_occupancy=initial_occupancy,
            initial_manipulator_positions=initial_positions,
            max_iterations=self.max_consult_iterations,
            include_material_consults=True
        )
        resolution = pipeline.generate()
        consults = list(getattr(resolution, "consults", resolution or []))
        stopped_reason = str(getattr(resolution, "stopped_reason", ""))
        if getattr(resolution, "simulation_result", None) is None:
            errors.append("CONSULT_RESOLUTION_NO_SIMULATION")
        return EventDrivenProgramBuildResult(
            valid=not errors,
            candidate=candidate,
            cycle=cycle,
            programs=programs,
            consults=consults,
            configuration=configuration,
            event_result=event_result,
            consult_resolution=resolution,
            errors=errors,
            notes=[
                f"cycle={cycle.start_time:.1f}..{cycle.end_time:.1f}",
                f"consults={len(consults)}",
                f"consult_stop={stopped_reason or 'n/a'}"
            ]
        )
