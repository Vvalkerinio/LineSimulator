from pathlib import Path


def test_gui_event_simulation_uses_deep_copied_configuration():
    source = Path('src/gui/simulation_tab.py').read_text()
    assert 'from copy import deepcopy' in source
    assert 'simulation_configuration = deepcopy(self.configuration)' in source
    assert 'EventDrivenSimulator(\n                        simulation_configuration' in source
    assert 'SimulationServicesFactory.create(\n                        simulation_configuration.manipulators' in source
