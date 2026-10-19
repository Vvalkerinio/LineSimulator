from pathlib import Path

def test_debug_checkbox_defaults_off():
    source=Path("src/gui/simulation_tab.py").read_text(encoding="utf-8")
    assert "Debug log (spowalnia symulację)" in source
    assert "self.debug_log.setChecked(False)" in source
    assert "with debug_mode(self.debug_log.isChecked()):" in source
