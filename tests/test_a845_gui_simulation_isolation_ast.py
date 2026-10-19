from pathlib import Path


def test_both_gui_simulators_use_isolated_configuration():
    event_source = Path('src/gui/simulation_tab.py').read_text()
    program_source = Path('src/gui/cyclogram_tab.py').read_text()
    assert 'simulation_configuration = deepcopy(self.configuration)' in event_source
    assert 'configuration=(\n                        deepcopy(self.configuration)' in program_source
