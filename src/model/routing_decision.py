from dataclasses import dataclass


@dataclass
class RoutingDecision:

    selected_station: int

    reason: str

    candidate_stations: list[int] | None = None