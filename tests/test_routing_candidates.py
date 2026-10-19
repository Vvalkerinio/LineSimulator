from src.model.station import Station

from src.core.station_manager import (
    StationManager
)

from src.core.routing_engine import (
    RoutingEngine
)


def test_available_candidates():

    manager = StationManager(
        [
            Station(
                id=9,
                name="A",
                enabled=True,
                min_process_time=10,
                max_process_time=300
            ),
            Station(
                id=10,
                name="B",
                enabled=True,
                min_process_time=10,
                max_process_time=300
            )
        ]
    )

    decision = (
        RoutingEngine(
            manager
        )
        .select_station(
            [9, 10]
        )
    )

    assert (
        decision.candidate_stations
        == [9, 10]
    )