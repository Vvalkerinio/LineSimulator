from src.core.shared_bath_selector import (
    SharedBathSelector
)
from src.core.event_driven_simulator import EventDrivenSimulator
from src.model.manipulator import Manipulator
from src.model.simulation_configuration import SimulationConfiguration
from src.model.station import Station


class EmptyStationManager:

    def is_available(self, station_id, current_time):
        return True


def test_selects_first_station_when_candidates_are_equivalent():
    selector = SharedBathSelector(
        EmptyStationManager()
    )

    selected = selector.select(
        [9, 10],
        0
    )

    assert selected == 9
    assert selector.last_recommended_time == 0.0


def test_percent_stagger_dispatches_early_enough_for_overlapping_bath_loads():
    stations = [
        Station(1, "Load", True, 0.0, 0.0, is_process_bath=False),
        Station(
            2, "Bath A", True, 230.0, 300.0,
            shared_bath_group="ODT",
            is_process_bath=True,
        ),
        Station(
            3, "Bath B", True, 230.0, 300.0,
            shared_bath_group="ODT",
            is_process_bath=True,
        ),
        Station(4, "Unload", True, 0.0, 0.0, is_process_bath=False),
    ]
    for station in stations:
        station.shared_bath_stagger_mode = "percent"
        station.shared_bath_stagger_value = 50.0
    configuration = SimulationConfiguration(
        stations=stations,
        manipulators=[
            Manipulator(
                id=1,
                position=1,
                lift_time=1.0,
                drop_time=1.0,
                travel_time_per_position=1.0,
            )
        ],
        hanger_count=2,
        entry_interval=60.0,
        minimum_manipulator_spacing=0.0,
    )

    result = EventDrivenSimulator(configuration).run()

    first_bath_entry = result.station_entry_times[1, 2]
    second_bath_entry = result.station_entry_times[2, 3]

    assert second_bath_entry == first_bath_entry + 115.0
    assert second_bath_entry < first_bath_entry + 230.0
