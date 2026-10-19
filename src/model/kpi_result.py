from dataclasses import dataclass


@dataclass
class KPIResult:
    simulation_time: float
    processed_events: int
    scheduled_transports: int
    completed_transports: int
    transports_per_hour: float
    pieces_per_transport: int = 7
    parts_per_hour: float = 0.0
    average_cycle_time: float | None = None
