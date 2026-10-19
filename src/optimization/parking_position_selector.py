from dataclasses import dataclass


@dataclass(frozen=True)
class ParkingDecision:
    position: int
    is_process_bath: bool
    forced_process_bath: bool
    distance_to_target: int
    reason: str


class ParkingPositionSelector:
    """Select non-process parking first; use process bath only as fallback."""

    def __init__(self, constraints):
        self.constraints = constraints

    def select(self, manipulator_id, current_positions, target_position,
               stations, zone_start, zone_end, path_is_safe=None):
        station_map = {int(station.id): station for station in stations}
        path_is_safe = path_is_safe or (lambda start, end: True)
        current = int(current_positions[int(manipulator_id) - 1])
        legal = []
        for position in range(int(zone_start), int(zone_end) + 1):
            if position not in station_map:
                continue
            if not self.constraints.is_legal_position(
                manipulator_id, position, current_positions
            ):
                continue
            if not path_is_safe(current, position):
                continue
            station = station_map[position]
            process = bool(getattr(station, "is_process_bath", True))
            legal.append((process, abs(int(target_position) - position),
                          abs(current - position), position))
        if not legal:
            raise ValueError(f"No legal parking position for M{manipulator_id}")
        non_process = [item for item in legal if item[0] is False]
        pool = non_process or legal
        process, target_distance, _, position = min(pool)
        return ParkingDecision(
            position=position,
            is_process_bath=process,
            forced_process_bath=bool(process and not non_process),
            distance_to_target=target_distance,
            reason=("nearest_legal_non_process" if non_process
                    else "no_legal_non_process_position")
        )
