from dataclasses import (
    dataclass,
    field
)

from typing import Any

_event_counter = 0


@dataclass(order=True)
class Event:

    sort_index: tuple = field(
        init=False,
        repr=False
    )

    time: float = field(
        compare=False
    )

    event_type: Any = field(
        compare=False
    )

    manipulator_id: int | None = field(
        compare=False
    )

    hanger_id: int | None = field(
        compare=False
    )

    source_station: int | None = field(
        compare=False
    )

    target_station: int | None = field(
        compare=False
    )

    def __post_init__(
        self
    ):
        global _event_counter

        _event_counter += 1

        self.sort_index = (
            self.time,
            _event_counter
        )