from pathlib import Path

from src.optimization.event_driven_candidate import EventDrivenCandidate
from src.optimization.optimization_report import OptimizationReport
from src.optimization.optimization_runner import CandidateResult
from src.optimization.theoretical_screening_study import (
    TheoreticalScreeningStudyResult,
)


def test_csv_exports_theoretical_and_event_metrics(tmp_path):
    candidate = EventDrivenCandidate((1, 5, 11, 17))
    theoretical = CandidateResult(
        candidate, "THEORETICAL", (0,), {
            "candidate_type": "THEORETICAL_CANDIDATE",
            "evaluation_phase": "THEORETICAL_SCREENING",
            "theoretical_possible_upper_bound": 13.25,
            "theoretical_nominal_upper_bound": 12.75,
            "theoretical_limiting_resource": "manipulator:M2",
            "theoretical_startup_access_seconds": 16.0,
            "theoretical_shared_bath_penalty": 0.1,
            "theoretical_start_spacing_margin": 2.0,
        }, ()
    )
    event = CandidateResult(
        candidate, "VALID", (-12.1,), {
            **theoretical.metrics,
            "candidate_type": "EVENT_CANDIDATE",
            "screened_by": "THEORETICAL",
            "theoretical_rank": 1,
            "event_throughput_per_hour": 12.1,
        }, ()
    )
    study = TheoreticalScreeningStudyResult(
        theoretical_results=[theoretical],
        finalist_results=[event],
        theoretical_evaluations=1,
        event_evaluations=1,
    )
    path = OptimizationReport().write_csv(tmp_path / "ranking.csv", study)
    text = Path(path).read_text(encoding="utf-8-sig")
    assert "candidate_type" in text
    assert "theoretical_possible_upper_bound" in text
    assert "THEORETICAL_CANDIDATE" in text
    assert "EVENT_CANDIDATE" in text
    assert "13.25" in text
    assert "12.1" in text
