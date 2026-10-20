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


def test_provisional_pickups_do_not_overlap_manipulator_tasks():
    station_values = {
        1: (0.0, 999.9, 0.0, False, None, 0.0, 999.9),
        3: (230.0, 300.0, 10.0, False, "ODT", 230.0, 350.0),
        4: (230.0, 300.0, 10.0, False, "ODT", 230.0, 350.0),
        5: (50.0, 90.0, 5.0, False, None, 50.0, 90.0),
        6: (50.0, 90.0, 5.0, False, None, 50.0, 90.0),
        8: (130.0, 160.0, 10.0, True, None, 130.0, 160.0),
        14: (30.0, 90.0, 5.0, False, None, 30.0, 90.0),
        15: (30.0, 90.0, 5.0, False, None, 30.0, 90.0),
        19: (220.0, 240.0, 10.0, True, None, 200.0, 240.0),
        20: (30.0, 90.0, 5.0, False, None, 30.0, 90.0),
        21: (30.0, 90.0, 5.0, False, None, 30.0, 90.0),
        22: (0.0, 999.9, 0.0, False, None, 0.0, 999.9),
    }
    stations = []
    for station_id, values in station_values.items():
        min_time, max_time, drip_time, is_process_bath, group, possible_min, possible_max = values
        stations.append(Station(
            station_id,
            f"Station {station_id}",
            True,
            min_time,
            max_time,
            shared_bath_group=group,
            drip_time=drip_time,
            is_process_bath=is_process_bath,
            possible_min_process_time=possible_min,
            possible_max_process_time=possible_max,
        ))
    for station in stations:
        if station.shared_bath_group == "ODT":
            station.shared_bath_stagger_mode = "percent"
            station.shared_bath_stagger_value = 85.0

    configuration = SimulationConfiguration(
        stations=stations,
        manipulators=[
            Manipulator(1, 4, 6.5, 6.5, 4.5, 1, 7),
            Manipulator(2, 11, 6.5, 6.5, 4.5, 5, 14),
            Manipulator(3, 16, 6.5, 6.5, 4.5, 12, 19),
            Manipulator(4, 22, 6.5, 6.5, 4.5, 18, 22),
        ],
        hanger_count=5,
        entry_interval=60.0,
        minimum_manipulator_spacing=2.0,
    )

    result = EventDrivenSimulator(configuration).run()

    tasks_by_manipulator = {}
    for task in result.manipulator_tasks:
        tasks_by_manipulator.setdefault(task.manipulator_id, []).append(task)
    for tasks in tasks_by_manipulator.values():
        tasks.sort(key=lambda task: task.start_time)
        assert all(
            later.start_time >= earlier.end_time
            for earlier, later in zip(tasks, tasks[1:])
        )
