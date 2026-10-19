from dataclasses import (
    dataclass
)


@dataclass
class ProgramWordExecution:

    manipulator_id: int

    cycle_no: int

    plc_index: int

    word_address: int

    logical_step_no: int

    word_kind: str

    word_value: int

    start_time: float

    end_time: float

    start_position: int

    end_position: int

    action: int

    hanger_id: int | None = None

    blocked_by_consult: bool = False

    status: str = "OK"