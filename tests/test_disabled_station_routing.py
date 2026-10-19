from src.model.station import (
    Station
)

from src.core.station_manager import (
    StationManager
)

from src.core.routing_engine import (
    RoutingEngine
)


def test_disabled_station_is_ignored():

    manager = StationManager(
        [
            Station(
                id=9,
                name="KTL_A",
                enabled=False,
                min_process_time=10,
                max_process_time=100
            ),
            Station(
                id=10,
                name="KTL_B",
                enabled=True,
                min_process_time=10,
                max_process_time=100
            )
        ]
    )

    decision = (
        RoutingEngine(
            manager
        ).select_station(
            [9, 10]
        )
    )

    assert (
        decision.selected_station
        == 10
    )