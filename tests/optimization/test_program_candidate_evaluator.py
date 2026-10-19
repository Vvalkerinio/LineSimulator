from types import SimpleNamespace

from src.model.station import Station
from src.optimization import (
    OptimizationCandidate,
    ProgramCandidateEvaluator
)


class Segment:
    def __init__(self, mid, start, end, p0, p1, kind):
        self.manipulator_id = mid
        self.start_time = start
        self.end_time = end
        self.start_position = p0
        self.end_position = p1
        self.segment_type = kind


def configuration():
    return SimpleNamespace(
        stations=[
            Station(1, "Load", True, 0, 0, is_process_bath=False),
            Station(2, "Bath", True, 10, 20, is_process_bath=True),
            Station(3, "Park", True, 0, 0, is_process_bath=False),
            Station(4, "Unload", True, 0, 0, is_process_bath=False)
        ],
        manipulators=[SimpleNamespace(id=mid, position=mid)
                      for mid in (1, 2, 3, 4)]
    )


def result(closed=True, max_ok=True):
    end_m2 = 2 if closed else 3
    compliance = SimpleNamespace(min_ok=True, max_ok=max_ok)
    return SimpleNamespace(
        timeline_segments=[
            Segment(1, 0, 2, 1, 1, "idle"),
            Segment(2, 0, 2, 2, end_m2, "empty_move"),
            Segment(3, 0, 2, 3, 3, "idle"),
            Segment(4, 0, 2, 4, 4, "idle")
        ],
        program_cycle_kpi={
            "program_cycle_time": 100.0,
            "throughput_per_hour": 72.0,
            "hangers_per_program_cycle": 2.0
        },
        consult_waits=[{"start_time": 10, "end_time": 15}],
        track_waits=[], track_guard_events=[], deadlocks=[],
        process_violations=[], process_compliance=[compliance],
        program_residence_audit={"valid": True},
        empty_pickup_warnings=[], drop_without_hanger_warnings=[],
        occupied_drop_warnings=[]
    )


def factory_for(fake_result):
    class FakeSimulator:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
        def run(self):
            return fake_result
    return FakeSimulator


def candidate():
    return OptimizationCandidate((1, 2, 3, 4), (1, 2, 3, 4))


def test_valid_candidate_is_ranked_with_real_metrics():
    evaluator = ProgramCandidateEvaluator(
        configuration(), programs={}, cycles=3,
        simulator_factory=factory_for(result())
    )
    evaluated = evaluator(candidate())
    assert evaluated.status == "VALID"
    assert evaluated.metrics["program_cycle_time"] == 100.0
    assert evaluated.metrics["gross_consult_wait"] == 5.0
    assert evaluated.metrics["empty_travel_time"] == 2.0
    assert evaluated.metrics["process_bath_idle_time"] == 0.0
    assert evaluated.metrics["final_positions"] == (1.0, 2.0, 3.0, 4.0)


def test_cycle_position_mismatch_rejects_candidate():
    evaluator = ProgramCandidateEvaluator(
        configuration(), programs={},
        simulator_factory=factory_for(result(closed=False))
    )
    evaluated = evaluator(candidate())
    assert evaluated.status == "REJECTED"
    assert "CYCLE_POSITION_NOT_CLOSED" in evaluated.rejection_reasons


def test_max_residence_rejects_candidate():
    evaluator = ProgramCandidateEvaluator(
        configuration(), programs={},
        simulator_factory=factory_for(result(max_ok=False))
    )
    evaluated = evaluator(candidate())
    assert evaluated.status == "REJECTED"
    assert "MAX_RESIDENCE" in evaluated.rejection_reasons


def test_base_configuration_is_not_mutated():
    config = configuration()
    evaluator = ProgramCandidateEvaluator(
        config, programs={}, simulator_factory=factory_for(result())
    )
    evaluator(OptimizationCandidate((4, 5, 6, 7), (4, 5, 6, 7)))
    assert [item.position for item in config.manipulators] == [1, 2, 3, 4]
