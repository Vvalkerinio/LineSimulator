from pathlib import Path


def test_deferred_predictive_pickup_waits_for_all_active_yields():
    source = Path('src/core/event_driven_simulator.py').read_text()
    assert 'future_yield_ends' in source
    assert 'retry_at = (' in source
    assert 'ready_at=retry_at' in source
    assert "if float(current_time) + 1e-9 < float(waiting.ready_at):" in source
    assert "max(future_yield_ends)" in source
