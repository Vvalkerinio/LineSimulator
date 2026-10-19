from dataclasses import dataclass


@dataclass
class WaitingTransport:

    hanger_id: int

    manipulator_id: int

    source_station: int

    target_station: int

    requested_at: float

    ready_at: float

    process_time: float