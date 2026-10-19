from types import SimpleNamespace

from src.model.manipulator_program import ManipulatorProgram
from src.model.manipulator_program_step import ManipulatorProgramStep
from src.model.program_consult import ProgramConsult
from src.model.station import Station
from src.optimization import (
    OptimizationCandidate,
    TrajectoryAwarePrepositionPlanner,
    TrajectoryAwareOptimizationPipeline,
    CandidateResult
)


class Segment:
    def __init__(self, mid, start, end, p0, p1):
        self.manipulator_id = mid
        self.start_time = start
        self.end_time = end
        self.start_position = p0
        self.end_position = p1
        self.segment_type = "idle" if p0 == p1 else "empty_move"


def config():
    stations = [
        Station(i, f"S{i}", True, 0, 999,
                is_process_bath=(i not in (1, 3, 5, 7, 9, 11)))
        for i in range(1, 13)
    ]
    manipulators = [
        SimpleNamespace(id=1, position=1, work_zone_start=1,
                        work_zone_end=4, travel_time_per_position=1.0),
        SimpleNamespace(id=2, position=3, work_zone_start=3,
                        work_zone_end=8, travel_time_per_position=1.0),
        SimpleNamespace(id=3, position=9, work_zone_start=7,
                        work_zone_end=10, travel_time_per_position=1.0),
        SimpleNamespace(id=4, position=11, work_zone_start=9,
                        work_zone_end=12, travel_time_per_position=1.0)
    ]
    return SimpleNamespace(
        stations=stations, manipulators=manipulators,
        minimum_manipulator_spacing=2
    )


def program():
    steps = [
        ManipulatorProgramStep(
            manipulator_id=2, step_no=1, cycle_time_start=0,
            cycle_time_end=0, station_id=3, plc_station_value=3,
            action=2, wait_time_01s=0, command_name="DROP"
        ),
        ManipulatorProgramStep(
            manipulator_id=2, step_no=2, cycle_time_start=10,
            cycle_time_end=10, station_id=8, plc_station_value=8,
            action=1, wait_time_01s=0, command_name="PICKUP"
        )
    ]
    return ManipulatorProgram(2, 200, steps=steps)


def consult():
    return ProgramConsult(2, 2, 4, 204, 3, 1, 1, 301,
                          0, 0, 0, 0, reason="test")


def result(block_position=None):
    segments = [
        Segment(1, 0, 20, 1, 1),
        Segment(2, 0, 20, 3, 3),
        Segment(3, 0, 20, 9, 9),
        Segment(4, 0, 20, 11, 11)
    ]
    if block_position is not None:
        segments[2] = Segment(3, 0, 20, block_position, block_position)
    return SimpleNamespace(
        timeline_segments=segments,
        consult_waits=[{
            "manipulator_id": 2,
            "source_plc_index": 4,
            "start_time": 2.0,
            "end_time": 10.0
        }]
    )


def test_planner_uses_real_wait_window_and_selects_closest_safe_non_process():
    decision = TrajectoryAwarePrepositionPlanner(config()).plan_for_consult(
        result(), {2: program()}, consult()
    )
    assert decision is not None
    assert decision.approach_position == 7
    assert decision.target_position == 8
    assert decision.travel_time == 4.0
    assert decision.net_idle_wait == 4.0


def test_planner_rejects_approach_conflicting_during_consult_window():
    # M3 at ST6 blocks both useful non-process approaches ST5 and ST7, so no useful approach remains.
    decision = TrajectoryAwarePrepositionPlanner(config()).plan_for_consult(
        result(block_position=6), {2: program()}, consult()
    )
    assert decision is None


def test_pipeline_passes_real_trajectory_decisions_to_transformer():
    candidate = OptimizationCandidate((1, 3, 9, 11), (1, 3, 9, 11))
    baseline_result = result()
    baseline = CandidateResult(candidate, "VALID", (10,), {
        "result": baseline_result
    })
    transformed = CandidateResult(candidate, "VALID", (8,), {})

    class Evaluator:
        programs = {2: program()}
        consults = [consult()]
        transformer = None
        def __init__(self, answer): self.answer = answer
        def __call__(self, _): return self.answer
        def __deepcopy__(self, memo): return self

    captured = {}
    class Transformer:
        def transform(self, programs, consults, candidate,
                      approach_positions_by_source=None):
            captured.update(approach_positions_by_source or {})
            return SimpleNamespace(valid=True, programs=programs,
                                   consults=consults, errors=[])

    class TransformedEvaluator(Evaluator):
        def __call__(self, _):
            assert self.transformer is not None
            self.transformer.transform(self.programs, self.consults, candidate)
            return transformed

    pipeline = TrajectoryAwareOptimizationPipeline(
        Evaluator(baseline), TransformedEvaluator(transformed),
        TrajectoryAwarePrepositionPlanner(config()), Transformer()
    )
    evaluated = pipeline.evaluate(candidate)
    assert evaluated.status == transformed.status
    assert evaluated.objective == transformed.objective
    assert (2, 4) in captured
    assert evaluated.metrics["baseline"] is baseline
    assert evaluated.metrics["rejection_phase"] == "TRANSFORMED"
