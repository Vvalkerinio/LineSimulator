from dataclasses import dataclass


@dataclass
class TrajectorySegment:

    manipulator_id: int

    start_position: float
    end_position: float

    start_time: float
    end_time: float

    reservation_id: object | None = None