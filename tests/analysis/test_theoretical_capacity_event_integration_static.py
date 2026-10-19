from pathlib import Path


def test_event_simulator_publishes_theoretical_capacity_report():
    source = Path("src/core/event_driven_simulator.py").read_text(encoding="utf-8")
    assert "TheoreticalCapacityAnalyzer().analyze" in source
    assert "route=route" in source
    assert "result.theoretical_capacity" in source
    assert "result.theoretical_capacity_text" in source
    assert "TheoreticalCapacityTextReport().render" in source
