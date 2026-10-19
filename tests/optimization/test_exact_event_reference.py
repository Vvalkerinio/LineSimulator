from copy import deepcopy
from types import SimpleNamespace

from src.optimization import (
    CandidateResult, EventDrivenCandidate, EventDrivenOptimizationStudy,
    EventDrivenStudySettings, ReferenceEventDrivenEvaluator
)


class CapturingSimulator:
    captured = []
    def __init__(self, configuration):
        self.captured.append(configuration)
    def run(self):
        return SimpleNamespace(
            final_time=3600.0, processed_events=10,
            scheduled_transports=5, completed_transports=0,
            deadlocks=[], process_violations=[], process_compliance=[],
            events=[], steady_state={"detected": True, "throughput": 12.0}
        )


def test_reference_uses_exact_configuration_without_candidate_applier():
    config = SimpleNamespace(
        stations=[], manipulators=[], marker="exact-current"
    )
    candidate = EventDrivenCandidate((99, 98, 97, 96), ())
    result = ReferenceEventDrivenEvaluator(
        config, simulator_factory=CapturingSimulator
    )(candidate)
    assert result.status == "VALID"
    assert result.metrics["candidate_type"] == "REFERENCE_EVENT"
    assert CapturingSimulator.captured[-1].marker == "exact-current"
    assert CapturingSimulator.captured[-1] is not config


def test_reference_is_visible_but_excluded_from_limit_and_rejection_count():
    reference_candidate = EventDrivenCandidate((4, 11, 16, 22), ())
    candidates = [EventDrivenCandidate((1, 3, 5, 7+i), ()) for i in range(100)]
    ref = CandidateResult(reference_candidate, "VALID", (0,),
                          {"candidate_type": "REFERENCE_EVENT"}, ())
    def reject(candidate):
        return CandidateResult(candidate, "REJECTED", (1,), {}, ("X",))
    result = EventDrivenOptimizationStudy(
        reject, None, EventDrivenStudySettings(100, 0),
        reference_evaluator=lambda _: ref,
        reference_candidate=reference_candidate
    ).run(candidates)
    assert len(result.reference_results) == 1
    assert len(result.screening_results) == 100
    assert len(result.ranking) == 101
    assert result.evaluated_candidates == 100
    assert result.rejected_candidates == 100
    assert result.ranking[0].metrics["candidate_type"] == "REFERENCE_EVENT"
