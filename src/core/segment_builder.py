import math

from src.model.segment_reservation import SegmentReservation


class SegmentBuilder:
    """Build bounded track reservations for integer or interpolated positions."""

    EPSILON = 1e-9

    @classmethod
    def _normalize_position(cls, value):
        value = float(value)
        nearest = round(value)
        if abs(value - nearest) <= cls.EPSILON:
            return float(nearest)
        return value

    @classmethod
    def _next_boundary(cls, current, target, direction):
        if direction > 0:
            boundary = math.floor(current) + 1.0
            return min(float(target), boundary)
        boundary = math.ceil(current) - 1.0
        return max(float(target), boundary)

    def build(
        self,
        manipulator_id: int,
        source_station: float,
        target_station: float,
        start_time: float,
        travel_time_per_position: float
    ):
        source = self._normalize_position(source_station)
        target = self._normalize_position(target_station)
        current_time = float(start_time)
        travel_time = float(travel_time_per_position)

        if not all(math.isfinite(value) for value in (
            source, target, current_time, travel_time
        )):
            raise ValueError("Track reservation values must be finite")
        if travel_time < 0.0:
            raise ValueError("travel_time_per_position cannot be negative")
        if abs(target - source) <= self.EPSILON:
            return []

        direction = 1 if target > source else -1
        current = source
        reservations = []
        # A move crosses at most ceil(distance) unit track segments. The extra
        # slot protects positions that start/end inside a segment.
        maximum_segments = int(math.ceil(abs(target - source))) + 1

        for _ in range(maximum_segments):
            remaining = target - current
            if abs(remaining) <= self.EPSILON:
                break
            next_position = self._next_boundary(current, target, direction)
            distance = abs(next_position - current)
            if distance <= self.EPSILON:
                raise RuntimeError(
                    "Track segment construction made no progress: "
                    f"source={source!r}, target={target!r}, current={current!r}"
                )
            end_time = current_time + distance * travel_time
            reservations.append(SegmentReservation(
                manipulator_id=manipulator_id,
                segment_start=min(current, next_position),
                segment_end=max(current, next_position),
                start_time=current_time,
                end_time=end_time
            ))
            current = self._normalize_position(next_position)
            current_time = end_time
        else:
            raise RuntimeError(
                "Track segment construction exceeded its mathematical bound: "
                f"source={source!r}, target={target!r}"
            )

        if abs(current - target) > self.EPSILON:
            raise RuntimeError(
                "Track segment construction did not reach target: "
                f"source={source!r}, target={target!r}, current={current!r}"
            )
        return reservations
