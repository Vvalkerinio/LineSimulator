from dataclasses import dataclass


@dataclass(slots=True)
class TransportRequest:

    hanger_id: int

    source_station: int

    target_station: int

    ready_at: float