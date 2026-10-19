from src.model.station import (
    Station
)

from src.core.process_violation_engine import (
    ProcessViolationEngine
)


def test_violation_detected():

    station = Station(
        id=5,
        name="P5",
        enabled=True,
        min_process_time=200,
        max_process_time=100
    )

    violation = (
        ProcessViolationEngine()
        .validate(
            station,
            actual_time=200
        )
    )

    assert violation is not None

    assert violation.station_id == 5