from src.core.program_driven_simulator import ProgramDrivenSimulator
from src.model.simulation_configuration import SimulationConfiguration


def simulator_with(mode_marker=None):
    configuration = SimulationConfiguration(
        stations=[],
        manipulators=[]
    )
    if mode_marker is not None:
        configuration.program_driven_track_guard_mode = mode_marker
    return ProgramDrivenSimulator(
        configuration=configuration,
        programs={}
    )


def test_track_guard_defaults_to_off():
    assert simulator_with()._track_guard_mode() == "off"


def test_track_guard_modes_are_normalized():
    assert simulator_with("warning")._track_guard_mode() == "warn"
    assert simulator_with("true")._track_guard_mode() == "enforce"
    assert simulator_with("unexpected")._track_guard_mode() == "off"
