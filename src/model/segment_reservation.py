from dataclasses import dataclass


@dataclass
class SegmentReservation:

    manipulator_id: int

    segment_start: int

    segment_end: int

    start_time: float

    end_time: float

    reservation_id: object | None = None