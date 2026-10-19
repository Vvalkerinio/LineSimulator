from pathlib import Path
from src.optimization import (
    CandidateResult, EventDrivenCandidate, EventDrivenOptimizationStudy,
    EventDrivenStudySettings
)


def test_event_only_study_keeps_all_screened_rows_and_never_calls_program():
    candidates = [EventDrivenCandidate((1, 3, 5, 7+i), ()) for i in range(20)]
    calls = []
    def event(candidate):
        calls.append(candidate)
        return CandidateResult(candidate, "VALID", (-candidate.start_positions[-1],),
                               {"event_throughput_per_hour": 1.0}, ())
    def program(_):
        raise AssertionError("ProgramDriven must not run in event-only study")
    result = EventDrivenOptimizationStudy(
        event, program, EventDrivenStudySettings(20, 5)
    ).run(candidates)
    assert len(calls) == 20
    assert len(result.ranking) == 20
    assert result.program_evaluations == 0
    assert result.evaluated_candidates == 20


def test_gui_event_columns_are_aligned_and_no_plc_columns_remain():
    source = Path("src/gui/optimization_tab.py").read_text(encoding="utf-8")
    assert '"Transporty"' in source
    assert '"MIN violations"' in source
    assert '"MAX violations"' in source
    assert '"Consult wait [s]"' not in source
    assert '"Parking proces [s]"' not in source
    assert "self.apply_button.setEnabled(False)" in source


def test_factory_skips_unmodified_reference_and_has_no_program_evaluator():
    source = Path(
        "src/optimization/event_driven_optimization_factory.py"
    ).read_text(encoding="utf-8")
    assert "islice(generated, 1, None)" in source
    assert "GeneratedProgramCandidateEvaluator" not in source
    assert "ReferenceProgramEvaluator" not in source


def test_event_report_does_not_access_parking_positions():
    source = Path("src/optimization/optimization_report.py").read_text()
    assert "parking_positions" not in source
    assert "shared_bath_parameters" in source
    assert "event_throughput_per_hour" in source
