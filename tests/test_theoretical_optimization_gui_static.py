from pathlib import Path


def test_gui_exposes_two_optimization_modes_and_finalists():
    source = Path("src/gui/optimization_tab.py").read_text(encoding="utf-8")
    assert '"Pełny EventDriven", "event"' in source
    assert '"Theoretical screening → EventDriven finał", "theoretical"' in source
    assert '"optimization_mode": self.optimization_mode.currentData()' in source
    assert 'settings.addRow("Liczba finalistów:", self.finalist_count)' in source
    assert 'theoretical_possible_upper_bound' in source
    assert 'f"UB {float(metrics[' in source


def test_factory_selects_theoretical_study_by_mode():
    source = Path("src/optimization/event_driven_optimization_factory.py").read_text()
    assert 'mode == "theoretical"' in source
    assert "TheoreticalScreeningStudy(" in source
    assert "TheoreticalScreeningSettings(" in source
