from dataclasses import (
    dataclass
)


@dataclass
class ProgramConsult:

    source_manipulator_id: int

    source_logical_step_no: int

    source_plc_index: int

    source_word_address: int

    target_manipulator_id: int

    target_logical_step_no: int

    target_plc_index: int

    target_word_address: int

    source_cycle_time_start: float

    source_cycle_time_end: float

    target_cycle_time_start: float

    target_cycle_time_end: float

    reason: str = "FOREIGN_ZONE"

    description: str = ""

    def to_text(
        self
    ):
        return (
            f"M{self.source_manipulator_id} "
            f"INDEX {self.source_plc_index} "
            f"(MW{self.source_word_address}) "
            f"WAIT UNTIL "
            f"M{self.target_manipulator_id} "
            f"INDEX {self.target_plc_index} "
            f"(MW{self.target_word_address}) "
            f"FINISHED"
        )