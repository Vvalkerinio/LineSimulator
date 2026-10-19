from types import SimpleNamespace

from src.optimization import (
    CandidateResult,
    EventDrivenCandidate,
    EventDrivenProgramBuildResult,
    GeneratedProgramCandidateEvaluator
)


def candidate(): return EventDrivenCandidate((1, 3, 5, 7), ())


def event_evaluation():
    return CandidateResult(
        candidate(), "VALID", (1,),
        {"event_throughput_per_hour": 10.0}, ()
    )


class BuildProvider:
    def __init__(self, build): self.build_result = build
    def build(self, _): return self.build_result


class Cycle:
    manipulator_initial_phase = {
        1: (1, 0), 2: (3, 0), 3: (5, 0), 4: (7, 0)
    }
    station_initial_phase = {2: 101}


def configuration():
    stations = [SimpleNamespace(id=i, is_process_bath=False) for i in range(1, 9)]
    manipulators = [SimpleNamespace(id=i, position=2*i-1) for i in range(1, 5)]
    return SimpleNamespace(stations=stations, manipulators=manipulators)


def build(valid=True, errors=None):
    return EventDrivenProgramBuildResult(
        valid=valid, candidate=candidate(), cycle=Cycle(),
        programs={i: object() for i in range(1, 5)},
        consults=[object(), object()], configuration=configuration(),
        errors=list(errors or [])
    )


class Segment:
    def __init__(self, mid, pos):
        self.manipulator_id = mid
        self.start_position = pos
        self.end_position = pos
        self.start_time = 0.0
        self.end_time = 100.0
        self.segment_type = "idle"


class ProgramResult:
    def __init__(self):
        self.deadlocks = []
        self.process_violations = []
        self.empty_pickup_warnings = []
        self.drop_without_hanger_warnings = []
        self.occupied_drop_warnings = []
        self.process_compliance = []
        self.program_residence_audit = {"valid": True}
        self.track_guard_events = []
        self.active_consults = []
        self.timeline_segments = [Segment(i, 2*i-1) for i in range(1, 5)]
        self.program_cycle_kpi = {
            "cycle_duration": 400.0,
            "throughput": 9.0,
            "hangers_per_cycle": 1.0
        }
        self.consult_waits = []
        self.track_waits = []


class Simulator:
    captured = []
    result = ProgramResult()
    def __init__(self, **kwargs): self.captured.append(kwargs)
    def run(self): return self.result


def test_valid_generated_program_reports_realization_gap():
    evaluator = GeneratedProgramCandidateEvaluator(
        cycles=8, simulator_factory=Simulator,
        program_builder=BuildProvider(build())
    )
    result = evaluator(event_evaluation())
    assert result.status == "VALID"
    assert result.metrics["program_throughput_per_hour"] == 9.0
    assert result.metrics["throughput_realization_gap"] == 1.0
    assert result.metrics["throughput_realization_ratio"] == 0.9
    assert result.metrics["consult_count"] == 2
    assert Simulator.captured[-1]["initial_station_occupancy"] == {2: 101}
    assert Simulator.captured[-1]["initial_manipulator_positions"] == {
        1: 1, 2: 3, 3: 5, 4: 7
    }


def test_program_material_error_is_prefixed_and_rejected():
    broken = ProgramResult()
    broken.empty_pickup_warnings = ["x"]
    class BrokenSimulator(Simulator): result = broken
    result = GeneratedProgramCandidateEvaluator(
        simulator_factory=BrokenSimulator,
        program_builder=BuildProvider(build())
    )(event_evaluation())
    assert result.status == "REJECTED"
    assert result.rejection_reasons == ("PROGRAM_EMPTY_PICKUP",)


def test_build_failure_does_not_run_program_simulator():
    called = []
    result = GeneratedProgramCandidateEvaluator(
        simulator_factory=lambda **kwargs: called.append(kwargs),
        program_builder=BuildProvider(build(False, ["EVENT_NO_VALID_CLOSED_CYCLE"]))
    )(event_evaluation())
    assert result.status == "REJECTED"
    assert result.rejection_reasons == (
        "BUILD_EVENT_NO_VALID_CLOSED_CYCLE",
    )
    assert result.metrics["evaluation_phase"] == "PROGRAM_BUILD"
    assert called == []
