from dataclasses import dataclass


@dataclass
class ManipulatorTimelineSegment:

    manipulator_id: int

    start_time: float
    end_time: float

    start_position: float
    end_position: float

    segment_type: str = "loaded_move"

    hanger_id: int | None = None

    pickup_time: float | None = None

    drop_time: float | None = None