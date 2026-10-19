from src.model.station import (
    Station
)

from src.core.process_time_engine import (
    ProcessTimeEngine
)


def test_process_time():

    station = Station(
        id=5,
        name="P5",
        enabled=True,
        min_process_time=123,
        max_process_time=999
    )

    engine = (
        ProcessTimeEngine()
    )

    assert (
        engine.process_time(
            station
        )
        == 123
    )