from pathlib import Path


def test_gui_contains_visible_preferred_parking_column_and_conversion():
    source = Path("src/gui/manipulator_tab.py").read_text(encoding="utf-8")
    assert '"Ulubiony parking [ST]"' in source
    assert "display_station_id" in source
    assert "internal_station_id" in source
    assert "preferred_parking_position" in source
