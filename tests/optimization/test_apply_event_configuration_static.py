from pathlib import Path


def test_gui_enables_apply_for_valid_event_candidate():
    source = Path("src/gui/optimization_tab.py").read_text(encoding="utf-8")
    assert 'candidate_type") == "EVENT_CANDIDATE"' in source
    assert "Program PLC i consulty nie" in source
    assert "program_build" not in source[source.index("def _application_ready"):]


def test_main_window_applies_positions_and_shared_bath_only():
    source = Path("src/gui/main_window.py").read_text(encoding="utf-8")
    method = source[source.index("def _apply_optimization_result"):
                    source.index("def _restore_optimization_backup")]
    assert "start_positions" in method
    assert "shared_bath_stagger_mode" in method
    assert "shared_bath_stagger_value" in method
    assert "cyclogram_tab.programs" not in method
    assert "cyclogram_tab.consults" not in method
