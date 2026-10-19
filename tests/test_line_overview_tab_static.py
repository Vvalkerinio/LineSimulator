from pathlib import Path


def source(name):
    return Path(name).read_text(encoding="utf-8")


def test_line_overview_is_registered_as_new_main_window_tab():
    text = source("src/gui/main_window.py")
    assert "LineOverviewTab" in text
    assert '"Widok linii"' in text
    assert "self.line_overview_tab" in text


def test_line_overview_has_shared_x_axis_playback_and_station_state():
    text = source("src/gui/line_overview_tab.py")
    assert "def _x_for_position" in text
    assert "StationAnimationWidget" in text
    assert "timeline_segments" in text
    assert "manipulator_width" in text
    assert "minimum_manipulator_spacing" in text
    assert "KOLIZJA" in text
    assert '"DÓŁ"' in text
    assert '"GÓRA"' in text
    assert '"100x"' in text


def test_both_simulation_engines_publish_to_line_overview():
    simulation = source("src/gui/simulation_tab.py")
    cyclogram = source("src/gui/cyclogram_tab.py")
    assert "self.line_overview_tab.update_result" in simulation
    assert "self.line_overview_tab.update_result" in cyclogram
