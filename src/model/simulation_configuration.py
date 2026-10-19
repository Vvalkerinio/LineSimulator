from dataclasses import (
    dataclass,
    field
)

from src.model.station import (
    Station
)
from src.model.manipulator import (
    Manipulator
)
from src.model.start_mode import (
    StartMode
)


@dataclass
class SimulationConfiguration:
    stations: list[Station]
    manipulators: list[Manipulator]

    hanger_count: int = 1
    entry_interval: float = 60.0
    pieces_per_transport: int = 7

    infinite_feed: bool = False
    feed_duration: float = 3600.0
    warmup_time: float = 1800.0
    steady_state_window: float = 300.0

    start_mode: StartMode = StartMode.EMPTY

    minimum_manipulator_spacing: float = 2.0

    shared_bath_groups: list = field(
        default_factory=list
    )
    program_index_addresses: dict = field(
        default_factory=lambda: {
            1: 500,
            2: 600,
            3: 700,
            4: 800
        }
    )

    program_station_offsets: dict = field(
        default_factory=lambda: {
            1: 0,
            2: 0,
            3: 0,
            4: 0
        }
    )
    consult_generation_mode: str = (
        "collision"
    )
    def effective_hanger_count(
        self
    ) -> int:
        if not self.infinite_feed:
            return self.hanger_count

        if self.entry_interval <= 0:
            return self.hanger_count

        return max(
            1,
            int(
                self.feed_duration
                //
                self.entry_interval
            )
        )

    def normalized_start_mode(
        self
    ) -> StartMode:
        self.start_mode = (
            StartMode.from_value(
                self.start_mode
            )
        )

        return self.start_mode
        program_index_addresses: dict = field(
            default_factory=lambda: {
                1: 500,
                2: 600,
                3: 700,
                4: 800
            }
        )

        program_station_offsets: dict = field(
            default_factory=lambda: {
                1: 0,
                2: 0,
                3: 0,
                4: 0
            }
        )
