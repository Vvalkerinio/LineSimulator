from pathlib import Path
def test_variant_a():
 s=Path('src/core/event_driven_simulator.py').read_text()
 assert 'proposal_respects_full_spacing' in s and 'FULL_SPACING_BLOCKED' in s and 'SHARED_BATH_ENTRY_DEFER_COMMIT' in s and "segment_type='drop_hold'" in s
