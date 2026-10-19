from src.optimization.event_driven_candidate import EventDrivenCandidate
from src.optimization.optimization_runner import CandidateResult
from src.optimization.theoretical_screening_study import (
    TheoreticalScreeningSettings,
    TheoreticalScreeningStudy,
)


def candidates(count):
    return [EventDrivenCandidate((1, 4 + i, 10 + i, 18 + i)) for i in range(count)]


def theoretical(candidate):
    score = sum(candidate.start_positions)
    return CandidateResult(
        candidate, "THEORETICAL", (0, score),
        {"candidate_type": "THEORETICAL_CANDIDATE", "proxy": score}, ()
    )


class EventEvaluator:
    def __init__(self):
        self.calls = []

    def __call__(self, candidate):
        self.calls.append(candidate)
        return CandidateResult(
            candidate, "VALID", (-100.0,),
            {"candidate_type": "EVENT_CANDIDATE", "event_throughput_per_hour": 100.0}, ()
        )


def test_all_candidates_are_theoretical_but_only_finalists_run_event():
    event = EventEvaluator()
    study = TheoreticalScreeningStudy(
        theoretical, event,
        TheoreticalScreeningSettings(screening_limit=12, finalist_count=3)
    ).run(candidates(12))
    assert study.theoretical_evaluations == 12
    assert study.event_evaluations == 3
    assert len(event.calls) == 3
    assert len(study.finalist_results) == 3
    assert all(item.metrics["candidate_type"] == "EVENT_CANDIDATE"
               for item in study.finalist_results)
    assert all(item.metrics["screened_by"] == "THEORETICAL"
               for item in study.finalist_results)


def test_theoretical_rows_are_not_applicable_event_results():
    event = EventEvaluator()
    study = TheoreticalScreeningStudy(
        theoretical, event,
        TheoreticalScreeningSettings(screening_limit=5, finalist_count=2)
    ).run(candidates(5))
    assert study.ranking[:2] == study.finalist_results
    assert all(item.status == "THEORETICAL" for item in study.theoretical_results)
    assert study.best.status == "VALID"
