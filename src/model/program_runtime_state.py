from dataclasses import (
    dataclass,
    field
)


@dataclass
class ProgramRuntimeState:

    manipulator_id: int

    current_plc_index: int = 1

    current_position: int = 1

    current_action: int = 2

    available_time: float = 0.0

    cycle_no: int = 1

    cycle_start_time: float = 0.0

    finished_cycle: bool = False

    carrying_hanger_id: int | None = None

    pickup_source_station: int | None = None

    pickup_start_time: float | None = None

    pickup_finish_time: float | None = None

    completed_indices: dict[int, float] = field(
        default_factory=dict
    )
