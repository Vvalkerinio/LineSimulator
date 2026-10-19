from dataclasses import dataclass


@dataclass
class QueueStatistics:

    station_id: int

    queue_length: int

    max_wait: float

    average_wait: float

    deadlock_count: int