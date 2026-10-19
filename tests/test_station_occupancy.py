from src.model.station import (
    Station
)

from src.core.station_manager import (
    StationManager
)


def test_station_becomes_occupied():

    manager = StationManager(
        [
            Station(
                id=1,
                name="P1",
                enabled=True,
                min_process_time=10,
                max_process_time=100
            )
        ]
    )

    manager.occupy(
        station_id=1,
        hanger_id=5,
        occupied_until=100
    )

    assert (
        manager.is_available(
            1,
            current_time=50
        )
        is False
    )