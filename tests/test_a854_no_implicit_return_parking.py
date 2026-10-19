from pathlib import Path


def test_event_transport_ends_at_drop_without_implicit_parking_or_yield():
    source = Path('src/core/assignment_selector.py').read_text()
    body = source[
        source.index('    def _return_position_after_drop('):
        source.index('    def _return_position_candidates(')
    ]
    candidates = source[
        source.index('    def _return_position_candidates('):
        source.index('    def _build_assignment(')
    ]
    assert 'return int(target_station)' in body
    assert '_candidate_yield_positions' not in body
    assert 'return [int(target_station)]' in candidates
