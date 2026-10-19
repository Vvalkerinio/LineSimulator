from src.core.station_manager import (
    StationManager
)

from src.model.station import (
    Station
)


def test_station_not_auto_released():

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

    #
    # Proces zakończony,
    # ale zawieszka nadal stoi
    # na stanowisku.
    #
    assert (
        manager.is_available(
            1,
            current_time=150
        )
        is False
    )


def test_station_released_explicitly():

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

    manager.release(
        1
    )

    assert (
        manager.is_available(
            1,
            current_time=150
        )
        is True
    )