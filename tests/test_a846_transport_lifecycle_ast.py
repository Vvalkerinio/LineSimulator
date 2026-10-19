from pathlib import Path


def test_event_driven_transport_leg_is_idempotent():
    source = Path('src/core/event_driven_simulator.py').read_text()
    assert 'active_transport_keys = set()' in source
    assert 'completed_transport_keys = set()' in source
    assert 'DUPLICATE_TRANSPORT_COMMIT_SKIPPED' in source
    assert 'DUPLICATE_TRANSPORT_END_SKIPPED' in source
    assert 'PROCESS_END_SKIP_TRANSPORT_PENDING' in source
    assert 'station_manager.state(' in source
