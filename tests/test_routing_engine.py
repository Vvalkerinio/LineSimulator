from src.model.station import Station

from src.core.station_manager import (
    StationManager
)

from src.core.routing_engine import (
    RoutingEngine
)


def test_shared_bath_first_free():

    stations = [
        Station(
            id=9,
            name="KTL_A",
            enabled=True,
            min_process_time=10,
            max_process_time=300,
            shared_bath_group="KTL_1"
        ),
        Station(
            id=10,
            name="KTL_B",
            enabled=True,
            min_process_time=10,
            max_process_time=300,
            shared_bath_group="KTL_1"
        )
    ]

    manager = StationManager(
        stations
    )

    manager.occupy(
        station_id=9,
        hanger_id=1,
        current_time=0
    )

    routing = RoutingEngine(
        manager
    )

    decision = (
        routing.select_station(
            [9, 10]
        )
    )

    assert (
        decision.selected_station
        == 10
    )