import json

from src.optimization import (
    CandidateResult,
    OptimizationCache,
    OptimizationCandidate,
    OptimizationReport,
    OptimizationStudy,
    OptimizationStudySettings
)


def candidate(value):
    return OptimizationCandidate(
        (1, 3, 5, 7),
        (1, 3, 5, 7 + value)
    )


class Evaluator:
    def __init__(self, phase, calls):
        self.phase = phase
        self.calls = calls

    def __call__(self, item):
        value = item.parking_positions[-1]
        self.calls.append((self.phase, value))
        rejected = value == 10
        cycle = float(value * 10 + (0 if self.phase == "final" else 5))
        return CandidateResult(
            candidate=item,
            status="REJECTED" if rejected else "VALID",
            objective=(cycle,),
            metrics={
                "program_cycle_time": cycle,
                "throughput_per_hour": 3600.0 / cycle,
                "hangers_per_cycle": 1.0,
                "gross_consult_wait": value,
                "track_wait": 0.0,
                "process_bath_idle_time": 0.0,
                "empty_travel_time": value / 2,
                "start_positions": item.start_positions,
                "final_positions": item.start_positions,
                "residence_record_count": 4
            },
            rejection_reasons=("TEST_REJECT",) if rejected else ()
        )


def test_two_phase_study_selects_only_best_valid_finalists(tmp_path):
    calls = []
    settings = OptimizationStudySettings(finalist_count=2)
    study = OptimizationStudy(
        Evaluator("screening", calls), Evaluator("final", calls),
        settings, cache=OptimizationCache(tmp_path, "study-a")
    ).run([candidate(3), candidate(1), candidate(2)])
    assert study.evaluated_candidates == 5
    assert len(study.finalist_results) == 2
    assert study.best.candidate.parking_positions[-1] == 8
    assert ("final", 10) not in calls
    assert study.rejected_candidates == 1


def test_second_run_uses_cache_and_does_not_call_evaluators(tmp_path):
    calls = []
    cache = OptimizationCache(tmp_path, "study-b")
    candidates = [candidate(1), candidate(2)]
    first = OptimizationStudy(
        Evaluator("screening", calls), Evaluator("final", calls),
        OptimizationStudySettings(finalist_count=1), cache=cache
    ).run(candidates)
    first_call_count = len(calls)
    second = OptimizationStudy(
        Evaluator("screening", calls), Evaluator("final", calls),
        OptimizationStudySettings(finalist_count=1), cache=cache
    ).run(candidates)
    assert len(calls) == first_call_count
    assert second.cache_hits == 3
    assert second.best.objective == first.best.objective


def test_progress_and_cancellation_stop_cleanly():
    calls = []
    progress = []
    state = {"cancel": False}

    def on_progress(event):
        progress.append(event)
        state["cancel"] = True

    study = OptimizationStudy(
        Evaluator("screening", calls), Evaluator("final", calls),
        OptimizationStudySettings(finalist_count=2),
        progress_callback=on_progress,
        cancel_requested=lambda: state["cancel"]
    ).run([candidate(1), candidate(2), candidate(3)])
    assert study.cancelled is True
    assert study.evaluated_candidates == 1
    assert len(progress) == 1


def test_reports_write_ranked_csv_and_json(tmp_path):
    calls = []
    study = OptimizationStudy(
        Evaluator("screening", calls), Evaluator("final", calls),
        OptimizationStudySettings(finalist_count=1)
    ).run([candidate(1), candidate(2)])
    report = OptimizationReport()
    csv_path = report.write_csv(tmp_path / "results.csv", study)
    json_path = report.write_json(tmp_path / "results.json", study)
    assert "event_throughput_per_hour" in csv_path.read_text(encoding="utf-8-sig")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "shared_bath_parameters" in payload["ranking"][0]["candidate"]
