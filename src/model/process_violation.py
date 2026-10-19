from dataclasses import dataclass


@dataclass
class ProcessViolation:

    station_id: int

    station_name: str

    required_time: float

    max_allowed_time: float