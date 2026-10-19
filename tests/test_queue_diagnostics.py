from src.core.queue_diagnostics import (
    QueueDiagnostics
)

from src.model.waiting_transport import (
    WaitingTransport
)


def test_queue_statistics():

    stats = (
        QueueDiagnostics()
        .build(
            station_id=5,
            waiting=[
                WaitingTransport(
                    hanger_id=1,
                    manipulator_id=1,
                    source_station=1,
                    target_station=5,
                    requested_at=0,
                    ready_at=0,
                    process_time=0
                ),
                WaitingTransport(
                    hanger_id=2,
                    manipulator_id=1,
                    source_station=2,
                    target_station=5,
                    requested_at=50,
                    ready_at=50,
                    process_time=0
                )
            ],
            deadlocks=[],
            current_time=100
        )
    )

    assert stats.queue_length == 2

    assert stats.max_wait == 100