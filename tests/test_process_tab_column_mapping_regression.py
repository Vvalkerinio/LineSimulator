from pathlib import Path


def test_process_tab_column_mapping_is_explicit_and_complete():
    source = Path("src/gui/process_tab.py").read_text(encoding="utf-8")
    expected = {
        "COLUMN_ID": 0,
        "COLUMN_NAME": 1,
        "COLUMN_ENABLED": 2,
        "COLUMN_PROCESS_BATH": 3,
        "COLUMN_POSSIBLE_MIN": 4,
        "COLUMN_MIN_TIME": 5,
        "COLUMN_MAX_TIME": 6,
        "COLUMN_POSSIBLE_MAX": 7,
        "COLUMN_DRIP_TIME": 8,
        "COLUMN_SHARED_BATH": 9,
    }
    for name, value in expected.items():
        assert f"{name} = {value}" in source


def test_load_and_save_use_all_process_column_constants():
    source = Path("src/gui/process_tab.py").read_text(encoding="utf-8")
    for name in (
        "COLUMN_POSSIBLE_MIN", "COLUMN_MIN_TIME", "COLUMN_MAX_TIME",
        "COLUMN_POSSIBLE_MAX", "COLUMN_DRIP_TIME", "COLUMN_SHARED_BATH"
    ):
        assert name in source
    assert "0.0 <= possible_min <= nominal_min <= nominal_max <= possible_max" in source


def test_empty_shared_bath_is_not_rendered_as_literal_none():
    source = Path("src/gui/process_tab.py").read_text(encoding="utf-8")
    assert '"" if shared is None else str(shared)' in source
    assert 'values["shared"].lower() in ("", "none")' in source
