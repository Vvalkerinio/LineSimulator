from dataclasses import (
    dataclass,
    field
)


@dataclass
class MaterialCycleCandidate:

    start_time: float

    end_time: float

    duration: float

    total_transports: int

    balance: dict[int, int] = field(
        default_factory=dict
    )

    transport_counts_by_manipulator: dict[int, int] = field(
        default_factory=dict
    )

    logical_steps_by_manipulator: dict[int, int] = field(
        default_factory=dict
    )

    station_initial_phase: dict[int, int] = field(
        default_factory=dict
    )

    station_final_phase: dict[int, int] = field(
        default_factory=dict
    )

    #
    # Nowe pola:
    #
    # Format:
    # {
    #     manipulator_id: (position, loaded)
    # }
    #
    # loaded:
    # 0 = manipulator pusty
    # 1 = manipulator niesie zawieszkę
    #
    manipulator_initial_phase: dict[int, tuple[int, int]] = field(
        default_factory=dict
    )

    manipulator_final_phase: dict[int, tuple[int, int]] = field(
        default_factory=dict
    )

    phase_errors: list[str] = field(
        default_factory=list
    )

    score: float = 0.0

    valid: bool = False

    messages: list[str] = field(
        default_factory=list
    )

    def balance_error(
        self
    ):
        return sum(
            abs(
                value
            )
            for value
            in self.balance.values()
        )

    def phase_error_count(
        self
    ):
        return len(
            self.phase_errors
        )

    def summary(
        self
    ):
        return (
            f"start={self.start_time:.1f}s, "
            f"end={self.end_time:.1f}s, "
            f"duration={self.duration:.1f}s, "
            f"transports={self.total_transports}, "
            f"balance_error={self.balance_error()}, "
            f"phase_errors={self.phase_error_count()}, "
            f"valid={self.valid}"
        )