from pathlib import Path


def test_main_window_integrates_optimization_and_application():
    source = Path("src/gui/main_window.py").read_text(encoding="utf-8")
    assert "OptimizationTab" in source
    assert "EventDrivenOptimizationFactory" in source
    assert '"Optymalizacja"' in source
    assert "_prepare_optimization" in source
    assert "_apply_optimization_result" in source
    assert "_optimization_backup" in source
    assert "shared_bath_stagger_value" in source


def test_stage7_buttons_require_revalidation():
    source = Path("src/gui/optimization_tab.py").read_text(encoding="utf-8")
    assert "Zastosuj wybrany wariant" in source
    assert "Końcowa walidacja" in source
    assert "evaluate_candidate_callback" in source
    assert 'candidate_type") == "EVENT_CANDIDATE"' in source
