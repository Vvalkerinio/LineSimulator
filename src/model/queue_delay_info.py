from dataclasses import dataclass


@dataclass
class QueueDelayInfo:

    station_id: int

    hanger_id: int

    waiting_time: float

    detected_at: float