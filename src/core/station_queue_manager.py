from collections import defaultdict

from src.analysis.queue_diagnostics import (
    QueueDiagnostics
)


class StationQueueManager:

    def __init__(
        self
    ):

        self._queues = defaultdict(
            list
        )

        self.diagnostics = (
            QueueDiagnostics()
        )

    def enqueue(
        self,
        station_id,
        transport
    ):

        self._queues[
            station_id
        ].append(
            transport
        )

        self.diagnostics.register_enqueue(
            len(
                self._queues[
                    station_id
                ]
            )
        )

    def dequeue(
        self,
        station_id
    ):

        queue = (
            self._queues[
                station_id
            ]
        )

        if not queue:

            return None

        result = queue.pop(
            0
        )

        self.diagnostics.register_dequeue(
            len(
                queue
            )
        )

        return result

    def peek(
        self,
        station_id
    ):

        queue = (
            self._queues[
                station_id
            ]
        )

        if not queue:

            return None

        return queue[0]

    def size(
        self,
        station_id
    ):

        return len(
            self._queues[
                station_id
            ]
        )

    def total_size(
        self
    ):

        return sum(
            len(queue)
            for queue
            in self._queues.values()
        )

    def stations(
        self
    ):

        return list(
            self._queues.keys()
        )