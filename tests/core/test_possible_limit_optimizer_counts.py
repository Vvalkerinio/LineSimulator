from types import SimpleNamespace
from src.optimization.event_driven_candidate_evaluator import EventDrivenCandidateEvaluator


def record(status, deviation=0.0):
    nominal_min_ok = status not in ("TRADEOFF_MIN", "HARD_MIN_VIOLATION")
    nominal_max_ok = status not in ("TRADEOFF_MAX", "HARD_MAX_VIOLATION")
    return SimpleNamespace(
        min_ok=nominal_min_ok,
        max_ok=nominal_max_ok,
        possible_min_ok=status != "HARD_MIN_VIOLATION",
        possible_max_ok=status != "HARD_MAX_VIOLATION",
        compliance_status=status,
        nominal_deviation=deviation,
    )


def test_tradeoffs_are_not_hard_failures():
    result = SimpleNamespace(process_compliance=[
        record("OK"), record("TRADEOFF_MIN", 2), record("TRADEOFF_MAX", 4)
    ])
    counts = EventDrivenCandidateEvaluator._compliance_counts(result)
    assert counts[1:5] == (1, 1, 0, 0)
    assert counts[5:] == (2, 6.0, 4.0)


def test_possible_limit_breach_is_hard_failure():
    result = SimpleNamespace(process_compliance=[
        record("HARD_MIN_VIOLATION", 10),
        record("HARD_MAX_VIOLATION", 20),
    ])
    counts = EventDrivenCandidateEvaluator._compliance_counts(result)
    assert counts[3] == 1
    assert counts[4] == 1
    assert counts[5] == 0
