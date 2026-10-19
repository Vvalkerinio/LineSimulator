from src.core.deadlock_detector import (
    DeadlockDetector
)

from src.model.waiting_transport import (
    WaitingTransport
)


def test_long_wait_detected():

    detector = (
        DeadlockDetector(
            max_wait_time=10
        )
    )

    transport = (
        WaitingTransport(
            hanger_id=1,
            manipulator_id=1,
            source_station=1,
            target_station=2,
            requested_at=0,
            ready_at=0,
            process_time=0
        )
    )

    result = (
        detector.detect(
            current_time=20,
            station_id=2,
            transport=transport
        )
    )

    assert result is not None