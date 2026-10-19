from dataclasses import dataclass


@dataclass(frozen=True)
class EventTrackConflict:
    manipulator_id: int
    neighbor_id: int
    conflict_start: float
    conflict_end: float
    minimum_gap: float
    required_gap: float
    side: str


class EventTrackSafetyCoordinator:
    """Continuous separation invariant for EventDriven trajectories."""

    EPSILON = 1e-9

    def __init__(self, manipulator_manager, trajectory_manager):
        self.manipulator_manager = manipulator_manager
        self.trajectory_manager = trajectory_manager
        self._ordered_manipulators = tuple(sorted(
            self.manipulator_manager.all(), key=lambda item: int(item.id)
        ))
        self._neighbors_by_id = {}
        for index, manipulator in enumerate(self._ordered_manipulators):
            neighbors = []
            if index > 0:
                neighbors.append((self._ordered_manipulators[index - 1], "left"))
            if index + 1 < len(self._ordered_manipulators):
                neighbors.append((self._ordered_manipulators[index + 1], "right"))
            self._neighbors_by_id[int(manipulator.id)] = tuple(neighbors)

    def _manipulators(self):
        return self._ordered_manipulators

    def _neighbors(self, manipulator_id):
        return self._neighbors_by_id.get(int(manipulator_id), ())

    @staticmethod
    def _candidate_position(start_position, end_position,
                            start_time, end_time, time_value):
        if end_time <= start_time:
            return float(end_position)
        ratio = (float(time_value) - float(start_time)) / (float(end_time) - float(start_time))
        ratio = max(0.0, min(1.0, ratio))
        return float(start_position) + (float(end_position) - float(start_position)) * ratio

    def _neighbor_position(self, neighbor, time_value):
        value = self.trajectory_manager.position_at(int(neighbor.id), float(time_value))
        if value is None or value == 0:
            return float(neighbor.position)
        return float(value)

    def _breakpoints(self, neighbor_id, start_time, end_time):
        points = {float(start_time), float(end_time)}
        for segment in self.trajectory_manager.segments_overlapping(
            int(neighbor_id), float(start_time), float(end_time)
        ):
            points.add(max(float(start_time), float(segment.start_time)))
            points.add(min(float(end_time), float(segment.end_time)))
        return sorted(points)

    def conflict_for_move(self, manipulator_id, start_position, end_position,
                          start_time, end_time, required_gap):
        required = max(0.0, float(required_gap))
        for neighbor, side in self._neighbors(manipulator_id):
            points = self._breakpoints(neighbor.id, start_time, end_time)
            if len(points) == 1:
                points.append(points[0])
            minimum = float("inf")
            for interval_start, interval_end in zip(points, points[1:]):
                candidate_a = self._candidate_position(
                    start_position, end_position, start_time, end_time, interval_start)
                candidate_b = self._candidate_position(
                    start_position, end_position, start_time, end_time, interval_end)
                neighbor_a = self._neighbor_position(neighbor, interval_start)
                neighbor_b = self._neighbor_position(neighbor, interval_end)
                gaps = ((candidate_a - neighbor_a, candidate_b - neighbor_b)
                        if side == "left" else
                        (neighbor_a - candidate_a, neighbor_b - candidate_b))
                minimum = min(minimum, *gaps)
                # The signed gap is piecewise linear, therefore its minimum on
                # an interval is always at one of the interval boundaries.
                if min(gaps) + self.EPSILON < required:
                    return EventTrackConflict(
                        int(manipulator_id), int(neighbor.id),
                        float(interval_start), float(interval_end),
                        float(minimum), required, side)
        return None

    def is_move_safe(self, **kwargs):
        return self.conflict_for_move(**kwargs) is None
