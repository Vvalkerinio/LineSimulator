import ast
from pathlib import Path


def _source(relative_path):
    return Path(relative_path).read_text(encoding="utf-8")


def test_gui_modules_are_valid_python():
    ast.parse(_source("src/gui/simulation_tab.py"))
    ast.parse(_source("src/gui/cyclogram_tab.py"))
    ast.parse(_source("src/core/event_driven_simulator.py"))


def test_simulation_tab_contains_progress_controls_and_callback():
    source = _source("src/gui/simulation_tab.py")
    assert "QProgressBar" in source
    assert "self.progress_bar.setRange(0, 100)" in source
    assert "Czas symulowany:" in source
    assert "QApplication.processEvents()" in source
    assert "progress_callback=self._update_simulation_progress" in source


def test_event_simulator_reports_incremental_and_final_progress():
    source = _source("src/core/event_driven_simulator.py")
    assert "progress_callback=None" in source
    assert "progress_percent = min(99" in source
    assert "progress_percent != self._last_progress_percent" in source
    assert "100, float(result.final_time), event_time_limit" in source


def test_program_table_has_station_and_read_only_plc_station_columns():
    source = _source("src/gui/cyclogram_tab.py")
    assert "self.table.setColumnCount(\n            12" in source
    assert '"Stanowisko",\n                "Stanowisko PLC"' in source
    assert "self.table.item(row, 3)" in source
    assert "self._plc_station_value(target_program, station_id)" in source
    assert "if column not in [3, 5, 6]:" in source


def test_empty_program_and_transfer_sequence_controls_exist():
    source = _source("src/gui/cyclogram_tab.py")
    assert '"Dodaj nowy krok"' in source
    assert '"Dodaj sekwencję przeładunku"' in source
    assert "def _ensure_program(self, manipulator_id):" in source
    assert "ManipulatorProgram(" in source
    assert "self._manual_step(program, 23, 2" in source
    assert "self._manual_step(program, 24, 1" in source
    assert "self._manual_step(program, 22, 2" in source


def test_plc_offset_formula_is_preserved():
    source = _source("src/gui/cyclogram_tab.py")
    expected = "int(station_id)\n            - int(program.station_offset)\n            + int(program.station_id_shift)"
    assert expected in source
