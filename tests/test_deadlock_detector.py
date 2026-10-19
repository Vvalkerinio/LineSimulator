from src.core.deadlock_detector import (
    DeadlockDetector
)

from src.model.waiting_transport import (
    WaitingTransport
)


def test_detect_deadlock():

    detector = (
        DeadlockDetector(
            max_wait_time=100
        )
    )

    transport = (
        WaitingTransport(
            hanger_id=1,
            manipulator_id=1,
            source_station=5,
            target_station=6,
            requested_at=0,
            ready_at=0,
            process_time=0
        )
    )

    result = (
        detector.detect(
            current_time=150,
            station_id=6,
            transport=transport
        )
    )

    assert result is not None

    assert (
        result.hanger_id
        == 1
    )