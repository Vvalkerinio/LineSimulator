from dataclasses import dataclass

from src.core.program_track_conflict_detector import ProgramTrackConflictDetector
from src.optimization.optimization_constraints import OptimizationConstraints


@dataclass(frozen=True)
class ConsultApproachDecision:
    manipulator_id: int
    source_plc_index: int
    target_position: int
    approach_position: int
    wait_start: float
    wait_end: float
    travel_time: float
    net_idle_wait: float
    reason: str


class TrajectoryAwarePrepositionPlanner:
    """Choose a safe non-process approach from real ProgramDriven timelines."""

    EPSILON = 1e-6

    def __init__(self, configuration, detector=None):
        self.configuration = configuration
        self.detector = detector or ProgramTrackConflictDetector(configuration)
        self.station_map = {
            int(item.id): item for item in getattr(configuration, "stations", [])
        }
        self.manipulator_map = {
            int(item.id): item
            for item in getattr(configuration, "manipulators", [])
        }
        self.constraints = OptimizationConstraints(
            getattr(configuration, "minimum_manipulator_spacing", 2.0)
        )

    @staticmethod
    def _value(item, name, default=None):
        if isinstance(item, dict):
            return item.get(name, default)
        return getattr(item, name, default)

    @staticmethod
    def _step_for_plc_index(program, plc_index):
        step_index = (max(1, int(plc_index)) - 1) // 3
        steps = list(getattr(program, "steps", []))
        if not 0 <= step_index < len(steps):
            return None
        return steps[step_index]

    def _segments_for(self, result, manipulator_id):
        return sorted(
            [item for item in getattr(result, "timeline_segments", [])
             if int(item.manipulator_id) == int(manipulator_id)],
            key=lambda item: (float(item.start_time), float(item.end_time))
        )

    def position_at(self, result, manipulator_id, time_value):
        manipulator = self.manipulator_map[int(manipulator_id)]
        position = float(getattr(manipulator, "position", 0.0))
        for segment in self._segments_for(result, manipulator_id):
            start = float(segment.start_time)
            end = float(segment.end_time)
            if time_value < start:
                break
            if start <= time_value <= end:
                return self.detector.position_on_segment(
                    start, end, segment.start_position,
                    segment.end_position, time_value
                )
            position = float(segment.end_position)
        return position

    def _positions_at(self, result, time_value):
        return tuple(
            self.position_at(result, mid, time_value)
            for mid in (1, 2, 3, 4)
        )

    def _movement_is_safe(self, result, manipulator_id, start_time, end_time,
                          source_position, target_position, wait_end):
        minimum = self.detector.minimum_spacing()
        for segment in getattr(result, "timeline_segments", []):
            if int(segment.manipulator_id) == int(manipulator_id):
                continue
            distance = self.detector.minimum_distance(
                start_time, end_time, source_position, target_position,
                segment.start_time, segment.end_time,
                segment.start_position, segment.end_position
            )
            if distance is not None and distance + self.EPSILON < minimum:
                return False
            # After arrival the manipulator remains at the approach position
            # until the consult releases.
            if end_time < wait_end:
                distance = self.detector.minimum_distance(
                    end_time, wait_end, target_position, target_position,
                    segment.start_time, segment.end_time,
                    segment.start_position, segment.end_position
                )
                if distance is not None and distance + self.EPSILON < minimum:
                    return False
        return True

    def _wait_record(self, consult_waits, manipulator_id, plc_index):
        matching = []
        for item in consult_waits:
            if int(self._value(item, "manipulator_id", -1)) != int(manipulator_id):
                continue
            if int(self._value(item, "source_plc_index", -1)) != int(plc_index):
                continue
            start = float(self._value(item, "start_time", 0.0))
            end = float(self._value(item, "end_time", start))
            if end > start:
                matching.append((end - start, start, end, item))
        return max(matching, default=None, key=lambda value: value[0])

    def plan_for_consult(self, result, programs, consult):
        manipulator_id = int(consult.source_manipulator_id)
        plc_index = int(consult.source_plc_index)
        wait = self._wait_record(
            getattr(result, "consult_waits", []), manipulator_id, plc_index
        )
        if wait is None:
            return None
        _, wait_start, wait_end, _ = wait
        program = programs.get(manipulator_id)
        protected_step = self._step_for_plc_index(program, plc_index)
        if protected_step is None:
            return None
        target_position = int(protected_step.station_id)
        current_position = self.position_at(result, manipulator_id, wait_start)
        current_positions = self._positions_at(result, wait_start)
        manipulator = self.manipulator_map[manipulator_id]
        wait_duration = wait_end - wait_start

        candidates = []
        for position in range(
            int(manipulator.work_zone_start),
            int(manipulator.work_zone_end) + 1
        ):
            station = self.station_map.get(position)
            if station is None or bool(getattr(station, "is_process_bath", True)):
                continue
            if not self.constraints.is_legal_position(
                manipulator_id, position, current_positions
            ):
                continue
            travel_time = abs(position - current_position) * float(
                manipulator.travel_time_per_position
            )
            if travel_time <= self.EPSILON or travel_time > wait_duration:
                continue
            move_end = wait_start + travel_time
            if not self._movement_is_safe(
                result, manipulator_id, wait_start, move_end,
                current_position, position, wait_end
            ):
                continue
            candidates.append((
                abs(target_position - position),
                max(0.0, wait_duration - travel_time),
                travel_time,
                position
            ))
        if not candidates:
            return None
        _, net_idle, travel_time, position = min(candidates)
        return ConsultApproachDecision(
            manipulator_id=manipulator_id,
            source_plc_index=plc_index,
            target_position=target_position,
            approach_position=position,
            wait_start=wait_start,
            wait_end=wait_end,
            travel_time=travel_time,
            net_idle_wait=net_idle,
            reason="SAFE_NON_PROCESS_APPROACH"
        )

    def plan(self, result, programs, consults):
        decisions = {}
        for consult in consults:
            decision = self.plan_for_consult(result, programs, consult)
            if decision is not None:
                decisions[(
                    decision.manipulator_id,
                    decision.source_plc_index
                )] = decision
        return decisions
