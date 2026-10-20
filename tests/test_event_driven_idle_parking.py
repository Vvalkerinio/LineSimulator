from src.core.event_driven_idle_parking import EventDrivenIdleParking
from src.core.event_driven_passing_detector import EventDrivenPassingDetector
from src.core.event_track_yield_planner import EventTrackYieldMove
from src.core.simulation_services_factory import SimulationServicesFactory
from src.core.station_manager import StationManager
from src.core.station_reservation_service import StationReservationService
from src.core.event_driven_simulator import EventDrivenSimulator
from src.analysis.theoretical_capacity_report import TheoreticalCapacityTextReport
from src.io.configuration_serializer import load_configuration
from src.model.manipulator import Manipulator
from src.model.simulation_configuration import SimulationConfiguration
from src.model.station import Station


def _create_idle_parking():
    stations = [
        Station(station_id, f"Station {station_id}", True, 0.0, 0.0)
        for station_id in range(1, 9)
    ]
    manipulators = [
        Manipulator(1, 6, 1.0, 1.0, 1.0, 1, 6),
        Manipulator(2, 8, 1.0, 1.0, 1.0, 6, 8),
    ]
    services = SimulationServicesFactory.create(manipulators, stations)
    transport_engine = services.transport_scheduler.assignment_selector.transport_engine
    parking = EventDrivenIdleParking(
        manipulator_manager=services.manipulator_manager,
        station_manager=StationManager(stations),
        station_reservation_service=StationReservationService(),
        track_service=services.track_service,
        passing_detector=EventDrivenPassingDetector(
            services.trajectory_manager,
            services.manipulator_manager,
        ),
        track_safety=transport_engine.track_safety,
        required_spacing=2.0,
    )
    return parking, manipulators[0], stations


def test_idle_parking_uses_safe_station_and_preserves_pickup_finish():
    parking, manipulator, stations = _create_idle_parking()

    plan = parking.plan(
        manipulator=manipulator,
        source_station=2,
        target_station=3,
        hanger_id=1,
        current_position=6,
        available_time=0.0,
        pickup_finish_time=20.0,
        stations=stations,
    )

    assert plan is not None
    assert plan.station_id == 4
    assert plan.departure_time == 0.0
    assert plan.arrival_time == 2.0
    assert plan.approach_start_time == 18.0


def test_idle_parking_is_skipped_when_there_is_no_safe_time_window():
    parking, manipulator, stations = _create_idle_parking()

    plan = parking.plan(
        manipulator=manipulator,
        source_station=2,
        target_station=3,
        hanger_id=1,
        current_position=6,
        available_time=0.0,
        pickup_finish_time=4.0,
        stations=stations,
    )

    assert plan is None


def test_simulator_parks_manipulator_at_station_four_before_delayed_pickup(
    monkeypatch,
):
    monkeypatch.setattr(
        TheoreticalCapacityTextReport,
        "render",
        lambda _self, _report: "",
    )
    stations = [
        Station(1, "Load", True, 0.0, 0.0, is_process_bath=False),
        Station(6, "ST6", True, 0.0, 0.0),
        Station(2, "Bath A", True, 230.0, 300.0, shared_bath_group="ODT"),
        Station(3, "Bath B", True, 230.0, 300.0, shared_bath_group="ODT"),
        Station(4, "ST4", True, 0.0, 0.0, is_process_bath=False),
        Station(8, "Unload", True, 0.0, 0.0, is_process_bath=False),
    ]
    for station in stations:
        station.shared_bath_stagger_mode = "percent"
        station.shared_bath_stagger_value = 50.0
    configuration = SimulationConfiguration(
        stations=stations,
        manipulators=[
            Manipulator(1, 6, 1.0, 1.0, 1.0, 1, 6),
            Manipulator(2, 8, 1.0, 1.0, 1.0, 6, 8),
        ],
        hanger_count=3,
        entry_interval=5.0,
        minimum_manipulator_spacing=2.0,
    )

    result = EventDrivenSimulator(configuration).run()

    parking_move = next(
        segment
        for segment in result.timeline_segments
        if segment.manipulator_id == 1
        and segment.segment_type == "empty_move"
        and segment.start_position == 6
        and segment.end_position == 4
    )
    return_move = next(
        segment
        for segment in result.timeline_segments
        if segment.manipulator_id == 1
        and segment.segment_type == "empty_move"
        and segment.start_position == 4
        and segment.end_position == 6
        and segment.start_time > parking_move.end_time
    )
    assert return_move.start_time > parking_move.end_time
    assert any(
        segment.manipulator_id == 1
        and segment.segment_type == "idle"
        and segment.start_position == 4
        and segment.start_time == parking_move.end_time
        and segment.end_time == return_move.start_time
        for segment in result.timeline_segments
    )


def test_idle_parking_retimes_existing_yield_instead_of_adding_a_second_move():
    _, manipulator, stations = _create_idle_parking()
    manipulator.travel_time_per_position = 4.5
    services = SimulationServicesFactory.create(
        [manipulator, Manipulator(2, 8, 1.0, 1.0, 4.5, 6, 8)],
        stations,
    )
    engine = services.transport_scheduler.assignment_selector.transport_engine
    planner = engine.yield_planner
    move = EventTrackYieldMove(
        yielding_manipulator_id=1,
        blocked_manipulator_id=2,
        start_position=6.0,
        end_position=4.0,
        start_time=267.5,
        end_time=276.5,
        blocked_target=6.0,
    )
    planner.commit(move)

    updated = planner.reschedule_for_parking(
        move,
        start_time=248.0,
        end_time=257.0,
    )

    assert updated is not None
    assert len(planner.moves) == 1
    assert planner.moves[0] == updated
    assert services.trajectory_manager.position_at(1, 248.0) == 6.0
    assert services.trajectory_manager.position_at(1, 257.0) == 4.0
    assert services.trajectory_manager.position_at(1, 267.5) == 4.0
    assert services.transport_scheduler.assignment_selector.availability.available_from(1) == 257.0


def test_simulator_continues_from_committed_yield_endpoint(monkeypatch):
    monkeypatch.setattr(
        TheoreticalCapacityTextReport,
        "render",
        lambda _self, _report: "",
    )
    configuration = load_configuration("configs/fsf.json")
    configuration.infinite_feed = False
    configuration.hanger_count = 9
    configuration.entry_interval = 60.0
    configuration.event_driven_max_time = 3000.0
    for station in configuration.stations:
        if getattr(station, "shared_bath_group", None) == "ODT":
            station.shared_bath_stagger_mode = "alternate"
            station.shared_bath_stagger_value = 95.0

    result = EventDrivenSimulator(configuration).run()

    yield_and_next_move = [
        (
            move,
            next(
                segment
                for segment in result.timeline_segments
                if segment.manipulator_id == 1
                and segment.segment_type == "empty_move"
                and segment.start_time == move.end_time
            ),
        )
        for move in result.event_track_yields
        if move.yielding_manipulator_id == 1
        and any(
            segment.manipulator_id == 1
            and segment.segment_type == "empty_move"
            and segment.start_time == move.end_time
            for segment in result.timeline_segments
        )
    ]
    assert yield_and_next_move
    last_yield, next_move = yield_and_next_move[-1]
    assert next_move.start_position == last_yield.end_position
