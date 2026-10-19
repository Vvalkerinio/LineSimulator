from dataclasses import (
    dataclass
)


@dataclass
class ManipulatorProgramStep:

    manipulator_id: int

    step_no: int

    cycle_time_start: float

    cycle_time_end: float

    station_id: int

    plc_station_value: int

    action: int

    wait_time_01s: int

    command_name: str

    station_name: str = ""

    source_station: int | None = None

    target_station: int | None = None

    source_name: str = ""

    target_name: str = ""

    hanger_id: int | None = None

    segment_type: str = ""

    crosses_foreign_zone: bool = False

    foreign_zone_owner: int | None = None

    status: str = "OK"

    def words(
        self
    ):
        return [
            int(
                self.plc_station_value
            ),
            int(
                self.action
            ),
            int(
                self.wait_time_01s
            )
        ]