from src.core.shared_bath_selector import (
    SharedBathSelector
)
from src.core.event_driven_simulator import EventDrivenSimulator
from src.core.predictive_pickup_scheduler import PredictivePickupScheduler
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


def test_process_end_commits_yield_to_clear_neighbor_from_pickup_station(monkeypatch):
    monkeypatch.setattr(
        PredictivePickupScheduler,
        "schedule_check",
        lambda *args, **kwargs: None,
    )
    stations = [
        Station(
            station_id,
            f"Station {station_id}",
            True,
            10.0,
            30.0,
            is_process_bath=station_id not in (1, 8),
        )
        for station_id in range(1, 9)
    ]
    configuration = SimulationConfiguration(
        stations=stations,
        manipulators=[
            Manipulator(1, 1, 1.0, 1.0, 1.0, 1, 5),
            Manipulator(2, 8, 1.0, 1.0, 1.0, 5, 8),
        ],
        hanger_count=1,
        entry_interval=60.0,
        minimum_manipulator_spacing=2.0,
    )

    result = EventDrivenSimulator(configuration).run()

    assert len(result.manipulator_tasks) == 7
    assert any(
        move.yielding_manipulator_id == 1
        and move.blocked_manipulator_id == 2
        and move.end_position <= 3
        for move in result.event_track_yields
    )
    assert result.deferred_transports == []
