from src.core.simulation_debug import debug_print
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class EventTrackYieldMove:
    yielding_manipulator_id: int
    blocked_manipulator_id: int
    start_position: float
    end_position: float
    start_time: float
    end_time: float
    blocked_target: float
    reason: str = 'RELEASE_BLOCKED_PATH'

class EventTrackYieldPlanner:
    """Proposes and commits the shortest safe empty displacement.

    Proposal is side-effect free. Commit updates trajectory and availability.
    Duplicate suppression lasts only until the committed yield finishes.
    """

    def __init__(self, manipulator_manager, availability, trajectory_manager, safety):
        self.manipulator_manager = manipulator_manager
        self.availability = availability
        self.trajectory_manager = trajectory_manager
        self.safety = safety
        self.moves = []
        self._active_until = {}

    def _find(self, manipulator_id):
        return next((item for item in self.manipulator_manager.all() if int(item.id) == int(manipulator_id)), None)

    @staticmethod
    def _zone(manipulator):
        start = int(getattr(manipulator, 'work_zone_start', 1))
        end = int(getattr(manipulator, 'work_zone_end', 22))
        return (min(start, end), max(start, end))

    @staticmethod
    def _key(conflict, blocked_target):
        return (int(conflict.manipulator_id), int(conflict.neighbor_id), int(round(float(blocked_target))))

    def propose(self, conflict, blocked_target, current_time, required_gap):
        if conflict is None:
            return None
        yielding = self._find(conflict.neighbor_id)
        if yielding is None:
            return None
        key = self._key(conflict, blocked_target)
        active_until = self._active_until.get(key)
        if active_until is not None and float(current_time) < active_until:
            return None
        start_time = max(float(current_time), float(self.availability.available_from(int(yielding.id))))
        start_position = self.trajectory_manager.position_at(int(yielding.id), start_time)
        if start_position is None or start_position == 0:
            start_position = float(yielding.position)
        required = float(required_gap)
        zone_start, zone_end = self._zone(yielding)
        if conflict.side == 'right':
            minimum_target = int(round(float(blocked_target) + required))
            candidates = range(max(minimum_target, int(round(start_position)) + 1, zone_start), zone_end + 1)
        else:
            maximum_target = int(round(float(blocked_target) - required))
            candidates = range(min(maximum_target, int(round(start_position)) - 1, zone_end), zone_start - 1, -1)
        travel_time_per_position = float(yielding.travel_time_per_position)
        for target in candidates:
            end_time = start_time + abs(float(target) - float(start_position)) * travel_time_per_position
            if end_time <= start_time:
                continue
            conflict_for_yield = self.safety.conflict_for_move(manipulator_id=int(yielding.id), start_position=float(start_position), end_position=float(target), start_time=start_time, end_time=end_time, required_gap=required)
            if conflict_for_yield is not None:
                continue
            return EventTrackYieldMove(yielding_manipulator_id=int(yielding.id), blocked_manipulator_id=int(conflict.manipulator_id), start_position=float(start_position), end_position=float(target), start_time=start_time, end_time=end_time, blocked_target=float(blocked_target))
        return None

    def commit(self, move):
        if move is None:
            return None
        yielding = self._find(move.yielding_manipulator_id)
        if yielding is None:
            return None
        key = (int(move.blocked_manipulator_id), int(move.yielding_manipulator_id), int(round(float(move.blocked_target))))
        self._active_until[key] = float(move.end_time)
        self.moves.append(move)
        self.trajectory_manager.add_move(manipulator_id=int(yielding.id), start_position=int(round(move.start_position)), end_position=int(round(move.end_position)), start_time=float(move.start_time), travel_time_per_position=float(yielding.travel_time_per_position))
        self.availability.reserve(int(yielding.id), float(move.end_time))
        yielding.position = int(round(move.end_position))
        debug_print(lambda: f'TRACK_YIELD_PLANNED blocked=M{move.blocked_manipulator_id} yielding=M{move.yielding_manipulator_id} move={move.start_position:.1f}->{move.end_position:.1f} time={move.start_time:.1f}->{move.end_time:.1f} target={move.blocked_target:.1f}')
        return move

    def reschedule_for_parking(self, move, start_time, end_time):
        if move not in self.moves:
            return None
        if (
            float(end_time) > float(move.start_time) + 1e-9
            or float(end_time) <= float(start_time)
            or abs(float(self.availability.available_from(
                move.yielding_manipulator_id
            )) - float(move.end_time)) > 1e-9
        ):
            return None
        yielding = self._find(move.yielding_manipulator_id)
        if yielding is None:
            return None
        if not self.trajectory_manager.replace_move(
            manipulator_id=move.yielding_manipulator_id,
            start_position=int(round(move.start_position)),
            end_position=int(round(move.end_position)),
            old_start_time=float(move.start_time),
            old_end_time=float(move.end_time),
            new_start_time=float(start_time),
            travel_time_per_position=float(yielding.travel_time_per_position),
        ):
            return None

        updated = replace(
            move,
            start_time=float(start_time),
            end_time=float(end_time),
        )
        self.moves[self.moves.index(move)] = updated
        key = (
            int(move.blocked_manipulator_id),
            int(move.yielding_manipulator_id),
            int(round(float(move.blocked_target))),
        )
        self._active_until[key] = float(end_time)
        self.availability.reserve(move.yielding_manipulator_id, float(end_time))
        debug_print(lambda: f'TRACK_YIELD_RESCHEDULED_FOR_PARKING M={move.yielding_manipulator_id} move={move.start_position:.1f}->{move.end_position:.1f} time={move.start_time:.1f}->{move.end_time:.1f} to={float(start_time):.1f}->{float(end_time):.1f}')
        return updated

    def plan(self, conflict, blocked_target, current_time, required_gap):
        proposal = self.propose(conflict=conflict, blocked_target=blocked_target, current_time=current_time, required_gap=required_gap)
        if proposal is None:
            if conflict is not None:
                debug_print(lambda: f'TRACK_YIELD_REJECTED blocked=M{conflict.manipulator_id} neighbor=M{conflict.neighbor_id} target={float(blocked_target):.1f} side={conflict.side}')
            return None
        return self.commit(proposal)
