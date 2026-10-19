from dataclasses import replace

from src.model.manipulator_timeline_segment import ManipulatorTimelineSegment


class YieldTimelineIntegrator:
    """Insert yield moves while removing stale overlapping idle intervals."""

    EPSILON = 1e-9

    def integrate(self, segments, yield_moves):
        result = list(segments)
        for move in sorted(yield_moves, key=lambda item: (item.start_time, item.end_time)):
            result = self._integrate_one(result, move)
        return sorted(result, key=lambda item: (item.manipulator_id, item.start_time, item.end_time))

    def _integrate_one(self, segments, move):
        updated = []
        for segment in segments:
            same_manipulator = int(segment.manipulator_id) == int(move.yielding_manipulator_id)
            overlaps = (
                float(segment.start_time) < float(move.end_time) - self.EPSILON
                and float(segment.end_time) > float(move.start_time) + self.EPSILON
            )
            if not same_manipulator or not overlaps or segment.segment_type != "idle":
                updated.append(segment)
                continue

            if float(segment.start_time) < float(move.start_time) - self.EPSILON:
                updated.append(replace(
                    segment,
                    end_time=float(move.start_time),
                    start_position=float(move.start_position),
                    end_position=float(move.start_position)
                ))
            if float(segment.end_time) > float(move.end_time) + self.EPSILON:
                updated.append(replace(
                    segment,
                    start_time=float(move.end_time),
                    start_position=float(move.end_position),
                    end_position=float(move.end_position)
                ))

        updated.append(ManipulatorTimelineSegment(
            manipulator_id=int(move.yielding_manipulator_id),
            start_time=float(move.start_time),
            end_time=float(move.end_time),
            start_position=float(move.start_position),
            end_position=float(move.end_position),
            segment_type="event_track_yield"
        ))
        return updated
