from src.model.station import Station
from src.model.hanger import Hanger

from src.core.station_manager import (
    StationManager
)

from src.core.hanger_manager import (
    HangerManager
)

from src.core.transport_manager import (
    TransportManager
)

from src.core.scheduler import (
    Scheduler
)


def test_scheduler_collects_request():

    stations = [
        Station(
            id=1,
            name="P1",
            enabled=True,
            min_process_time=10,
            max_process_time=100
        ),
        Station(
            id=2,
            name="P2",
            enabled=True,
            min_process_time=10,
            max_process_time=100
        )
    ]

    station_manager = (
        StationManager(
            stations
        )
    )

    hanger_manager = (
        HangerManager()
    )

    transport_manager = (
        TransportManager()
    )

    hanger = Hanger(
        id=1,
        current_station=1,
        route=[1, 2]
    )

    hanger.entered_station_at = 0

    hanger_manager.add_hanger(
        hanger
    )

    scheduler = Scheduler(
        station_manager,
        hanger_manager,
        transport_manager
    )

    requests = (
        scheduler.collect_requests(
            current_time=20
        )
    )

    assert len(requests) == 1

    assert (
        requests[0].source_station
        == 1
    )

    assert (
        requests[0].target_station
        == 2
    )