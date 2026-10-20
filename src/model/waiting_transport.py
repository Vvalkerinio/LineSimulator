from dataclasses import dataclass
from src.model.scheduled_transport import ScheduledTransport


@dataclass
class WaitingTransport:

    hanger_id: int

    manipulator_id: int

    source_station: int

    target_station: int

    requested_at: float

    ready_at: float

    process_time: float

    provisional: bool = False

    earliest_pickup_time: float | None = None

    provisional_assignment: ScheduledTransport | None = None

    provisional_reservation_id: str | None = None