from types import SimpleNamespace

from src.core.assignment_selector import AssignmentSelector
from src.core.simulation_services_factory import SimulationServicesFactory


class DummyTransportEngine:
    pass


class DummyManipulatorManager:
    def all(self):
        return []


def station(station_id, process, enabled=True):
    return SimpleNamespace(
        id=station_id,
        enabled=enabled,
        is_process_bath=process
    )


def manipulator(zone_start=1, zone_end=9, home=1):
    return SimpleNamespace(
        id=1,
        position=home,
        parking_position=home,
        work_zone_start=zone_start,
        work_zone_end=zone_end
    )


def selector(stations):
    return AssignmentSelector(
        manipulator_manager=DummyManipulatorManager(),
        availability=None,
        transport_engine=DummyTransportEngine(),
        stations=stations
    )


def test_odt_shared_bath_drop_returns_to_nearest_non_process_station():
    stations = [
        station(1, False),
        station(3, True),
        station(4, True),
        station(5, False),
        station(6, False),
    ]
    item = selector(stations)
    assert item._return_position_after_drop(manipulator(), 1, 4) == 4
    assert item._return_position_after_drop(manipulator(), 1, 3) == 3


def test_disabled_non_process_station_is_not_used_for_return():
    stations = [
        station(3, True),
        station(4, True),
        station(5, False, enabled=False),
        station(6, False),
    ]
    assert selector(stations)._return_position_after_drop(
        manipulator(), 1, 4
    ) == 4


def test_process_bath_is_fallback_only_without_non_process_station_in_zone():
    stations = [
        station(3, True),
        station(4, True),
        station(10, False),
    ]
    assert selector(stations)._return_position_after_drop(
        manipulator(zone_start=1, zone_end=9), 1, 4
    ) == 4


def test_non_process_target_keeps_existing_behavior():
    stations = [station(4, True), station(5, False)]
    assert selector(stations)._return_position_after_drop(
        manipulator(), 4, 5
    ) == 5


def test_services_factory_passes_station_classification_to_selector():
    stations = [station(4, True), station(5, False)]
    manip = SimpleNamespace(
        id=1, position=1, parking_position=1,
        work_zone_start=1, work_zone_end=9,
        lift_time=1.0, drop_time=1.0,
        travel_time_per_position=1.0
    )
    services = SimulationServicesFactory.create([manip], stations)
    assignment_selector = services.transport_scheduler.assignment_selector
    assert assignment_selector.station_map[4].is_process_bath is True
    assert assignment_selector.station_map[5].is_process_bath is False
