from src.model.station import Station
from src.core.station_manager import (
    StationManager
)


def test_station_occupancy():

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

    assert manager.is_free(1)

    manager.occupy(
        station_id=1,
        hanger_id=5,
        current_time=0
    )

    assert not manager.is_free(1)
