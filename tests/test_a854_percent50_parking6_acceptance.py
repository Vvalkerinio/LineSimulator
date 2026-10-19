from pathlib import Path


def test_no_implicit_return_parking_is_kept_separate_from_yield():
    source = Path("src/core/assignment_selector.py").read_text()
    body = source[source.index("    def _return_position_after_drop("):source.index("    def _return_position_candidates(")]
    assert "return int(target_station)" in body
    assert "_candidate_yield_positions" not in body


def test_event_entry_is_not_suppressed_by_global_wip_admission():
    source = Path("src/core/event_driven_simulator.py").read_text()
    assert "ENTRY_ADMISSION_DEFERRED" not in source
    assert "event_driven_max_wip" not in source
