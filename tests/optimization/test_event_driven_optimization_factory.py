from pathlib import Path


def test_main_window_uses_event_driven_factory_by_default():
    source = Path("src/gui/main_window.py").read_text(encoding="utf-8")
    assert "EventDrivenOptimizationFactory" in source
    assert "OptimizationStudyFactory(" not in source


def test_optimization_table_uses_shared_bath_not_parking():
    source = Path("src/gui/optimization_tab.py").read_text(encoding="utf-8")
    assert '"Shared Bath"' in source
    assert "candidate.parking_positions" not in source
    assert "program_throughput_per_hour" in source
    assert "throughput_realization_ratio" in source
