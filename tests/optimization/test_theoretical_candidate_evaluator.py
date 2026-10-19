from copy import deepcopy

from src.io.configuration_serializer import create_default_configuration
from src.optimization.event_driven_candidate import EventDrivenCandidate
from src.optimization.theoretical_candidate_evaluator import TheoreticalCandidateEvaluator


def candidate_from_configuration(configuration, offset=0):
    starts = tuple(int(item.position) + offset for item in configuration.manipulators)
    return EventDrivenCandidate(starts)


def test_theoretical_evaluator_does_not_run_event_simulator_and_publishes_proxy_metrics():
    configuration = create_default_configuration()
    candidate = candidate_from_configuration(configuration)
    result = TheoreticalCandidateEvaluator(configuration)(candidate)
    assert result.status in ("THEORETICAL", "REJECTED")
    assert result.metrics["candidate_type"] == "THEORETICAL_CANDIDATE"
    assert "theoretical_possible_upper_bound" in result.metrics
    assert "theoretical_startup_access_seconds" in result.metrics
    assert "theoretical_start_spacing_margin" in result.metrics
    assert len(result.objective) == 7


def test_start_positions_change_candidate_specific_proxy():
    configuration = create_default_configuration()
    first = TheoreticalCandidateEvaluator(configuration)(
        candidate_from_configuration(configuration)
    )
    moved = deepcopy(configuration)
    starts = []
    for item in moved.manipulators:
        starts.append(min(int(item.work_zone_end), int(item.position) + 1))
    second = TheoreticalCandidateEvaluator(configuration)(
        EventDrivenCandidate(tuple(starts))
    )
    assert (
        first.metrics["theoretical_startup_access_seconds"],
        first.metrics["theoretical_zone_center_penalty"],
    ) != (
        second.metrics["theoretical_startup_access_seconds"],
        second.metrics["theoretical_zone_center_penalty"],
    )
