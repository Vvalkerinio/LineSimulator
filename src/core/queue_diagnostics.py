from src.model.queue_statistics import (
    QueueStatistics
)

from src.model.waiting_transport import (
    WaitingTransport
)

from src.model.deadlock_info import (
    DeadlockInfo
)


class QueueDiagnostics:

    def build(
        self,
        station_id: int,
        waiting: list[WaitingTransport],
        deadlocks: list[DeadlockInfo],
        current_time: float
    ) -> QueueStatistics:

        waits = [
            current_time - item.requested_at
            for item in waiting
        ]

        max_wait = (
            max(waits)
            if waits
            else 0.0
        )

        average_wait = (
            sum(waits) / len(waits)
            if waits
            else 0.0
        )

        station_deadlocks = [
            d
            for d in deadlocks
            if d.station_id == station_id
        ]

        return QueueStatistics(
            station_id=
                station_id,
            queue_length=
                len(waiting),
            max_wait=
                max_wait,
            average_wait=
                average_wait,
            deadlock_count=
                len(station_deadlocks)
        )