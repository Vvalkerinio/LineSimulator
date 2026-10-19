from dataclasses import dataclass


@dataclass
class DeadlockInfo:

    station_id: int

    hanger_id: int

    waiting_time: float

    threshold: float

    detected_at: float