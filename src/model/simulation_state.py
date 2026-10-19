from dataclasses import (
    dataclass,
    field
)


@dataclass
class SimulationState:

    current_time: float = 0.0

    #
    # Legacy PlantSimulator
    #
    station_hangers: dict[int, int] = field(
        default_factory=dict
    )

    station_occupied_until: dict[int, float] = field(
        default_factory=dict
    )

    manipulator_positions: dict[int, int] = field(
        default_factory=dict
    )

    completed_events: int = 0

    scheduled_transports: list = field(
        default_factory=list
    )

    completed_transports: int = 0

    #
    # Event Driven Engine
    #
    active_hangers: set[int] = field(
        default_factory=set
    )

    completed_hangers: int = field(
        default=0
    )

    hanger_positions: dict[int, int] = field(
        default_factory=dict
    )

    hanger_route_index: dict[int, int] = field(
        default_factory=dict
    )

    waiting_hangers: set[int] = field(
        default_factory=set
    )

    #
    # 11.0e.2 FIFO queues
    #
    waiting_by_station: dict[int, list] = field(
        default_factory=dict
    )

    station_entry_times: dict = field(
        default_factory=dict
    )

    pending_process_end_times: dict = field(
        default_factory=dict
    )

    #
    # Lead Time diagnostics
    #
    # Pierwsza próba wejścia na linię.
    #
    hanger_requested_entry_time: dict = field(
        default_factory=dict
    )

    #
    # Faktyczne wejście na stanowisko załadunku.
    #
    hanger_actual_entry_time: dict = field(
        default_factory=dict
    )