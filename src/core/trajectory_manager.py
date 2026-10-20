from bisect import bisect_left, bisect_right

from src.model.position_sample import PositionSample
from src.model.trajectory_segment import TrajectorySegment


class TrajectoryManager:
    """Indexed trajectory history with logarithmic position lookup."""

    def __init__(self):
        self._trajectories = {}
        self._segments = []
        self._segments_by_manipulator = {}
        self._segment_start_times = {}
        self._revision = 0

    @property
    def revision(self):
        return self._revision

    def _insert_segment(self, segment):
        self._segments.append(segment)
        manipulator_id = int(segment.manipulator_id)
        segments = self._segments_by_manipulator.setdefault(manipulator_id, [])
        starts = self._segment_start_times.setdefault(manipulator_id, [])
        start_time = float(segment.start_time)
        if not starts or start_time >= starts[-1]:
            starts.append(start_time)
            segments.append(segment)
        else:
            index = bisect_right(starts, start_time)
            starts.insert(index, start_time)
            segments.insert(index, segment)
        self._revision += 1

    def add_move(self, manipulator_id, start_position, end_position,
                 start_time, travel_time_per_position,
                 reservation_id=None):
        if start_position == end_position:
            self._trajectories[manipulator_id] = [
                PositionSample(start_time, start_position)
            ]
            self._insert_segment(TrajectorySegment(
                manipulator_id=manipulator_id,
                start_position=start_position,
                end_position=end_position,
                start_time=start_time,
                end_time=start_time,
                reservation_id=reservation_id,
            ))
            return
        direction = 1 if end_position > start_position else -1
        samples = []
        current_position = start_position
        current_time = start_time
        samples.append(PositionSample(current_time, current_position))
        while current_position != end_position:
            current_position += direction
            current_time += travel_time_per_position
            samples.append(PositionSample(current_time, current_position))
        self._trajectories[manipulator_id] = samples
        self._insert_segment(TrajectorySegment(
            manipulator_id=manipulator_id,
            start_position=start_position,
            end_position=end_position,
            start_time=start_time,
            end_time=samples[-1].time,
            reservation_id=reservation_id,
        ))

    def remove_reservation(self, reservation_id):
        self._segments = [
            segment for segment in self._segments
            if segment.reservation_id != reservation_id
        ]
        self._segments_by_manipulator = {}
        self._segment_start_times = {}
        for segment in sorted(
            self._segments,
            key=lambda item: float(item.start_time),
        ):
            manipulator_id = int(segment.manipulator_id)
            self._segments_by_manipulator.setdefault(
                manipulator_id, []
            ).append(segment)
            self._segment_start_times.setdefault(
                manipulator_id, []
            ).append(float(segment.start_time))
        self._revision += 1

    def active_segments(self, start_time, end_time):
        result = []
        for manipulator_id in self._segments_by_manipulator:
            result.extend(self.segments_overlapping(
                manipulator_id, start_time, end_time
            ))
        return result

    def segments_for(self, manipulator_id):
        return list(self._segments_by_manipulator.get(int(manipulator_id), ()))

    def segments_overlapping(self, manipulator_id, start_time, end_time):
        manipulator_id = int(manipulator_id)
        segments = self._segments_by_manipulator.get(manipulator_id, ())
        starts = self._segment_start_times.get(manipulator_id, ())
        if not segments or end_time < start_time:
            return []
        stop = bisect_right(starts, float(end_time))
        begin = max(0, bisect_left(starts, float(start_time)) - 1)
        while begin > 0 and float(segments[begin - 1].end_time) >= start_time:
            begin -= 1
        return [
            segment for segment in segments[begin:stop]
            if float(segment.end_time) >= start_time
            and float(segment.start_time) <= end_time
        ]

    @staticmethod
    def _segment_position_at(segment, time_value):
        if segment.end_time <= segment.start_time:
            return segment.end_position
        if time_value <= segment.start_time:
            return segment.start_position
        if time_value >= segment.end_time:
            return segment.end_position
        ratio = ((time_value - segment.start_time)
                 / (segment.end_time - segment.start_time))
        return segment.start_position + (
            segment.end_position - segment.start_position
        ) * ratio

    def position_at(self, manipulator_id, time_value):
        manipulator_id = int(manipulator_id)
        segments = self._segments_by_manipulator.get(manipulator_id, ())
        starts = self._segment_start_times.get(manipulator_id, ())
        if not segments:
            return 0
        index = bisect_right(starts, float(time_value)) - 1
        if index < 0:
            return segments[0].start_position
        segment = segments[index]
        if float(time_value) <= float(segment.end_time):
            return self._segment_position_at(segment, float(time_value))
        return segment.end_position
