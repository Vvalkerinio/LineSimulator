from pathlib import Path


def test_route_tab_was_removed_from_main_window():
    source = Path("src/gui/main_window.py").read_text(encoding="utf-8")
    assert '"Trasa"' not in source
    assert "_create_route_tab" not in source


def test_trajectory_uses_vertical_resizable_splitter():
    source = Path("src/gui/manipulator_trajectory_tab.py").read_text(encoding="utf-8")
    assert "QSplitter" in source
    assert "QSplitter(Qt.Vertical)" in source
    assert "trajectory_splitter.addWidget(self.view)" in source
    assert "trajectory_splitter.addWidget(self.station_animation)" in source
    assert "setHandleWidth(8)" in source
    assert "_station_animation_last_size" in source
