from pathlib import Path


def test_results_tab_supports_object_and_dictionary_deadlocks():
    source = Path("src/gui/results_tab.py").read_text(encoding="utf-8")
    assert "isinstance(deadlock, dict)" in source
    assert "EVENT_TRACK_SAFETY_INVARIANT_BROKEN" in source
    assert "getattr(\n                deadlock,\n                \"hanger_id\"" in source
