from pathlib import Path


def test_deferred_cleanup_is_idempotent_after_successful_commit():
    source = Path('src/core/event_driven_simulator.py').read_text()
    wake = source[
        source.index('        def wake_deferred_transports'):
        source.index('        for hanger in hangers:', source.index('        def wake_deferred_transports'))
    ]
    assert 'deferred_transports.pop(hanger_id, None)' in wake
    assert 'del deferred_transports[hanger_id]' not in wake
