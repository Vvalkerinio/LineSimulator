from types import SimpleNamespace
from src.core.event_track_safety_coordinator import EventTrackSafetyCoordinator
from src.core.trajectory_manager import TrajectoryManager


class Manager:
    def __init__(self, items): self.items = items
    def all(self): return self.items


def items(*positions):
    return [SimpleNamespace(id=i + 1, position=p) for i, p in enumerate(positions)]


def guard(values, trajectories=None):
    return EventTrackSafetyCoordinator(Manager(values), trajectories or TrajectoryManager())


def test_static_neighbor_blocks_adjacent_target():
    conflict = guard(items(4, 15, 20, 22)).conflict_for_move(
        1, 4, 14, 0, 10, 2)
    assert conflict is not None and conflict.neighbor_id == 2


def test_mid_move_conflict_is_detected_continuously():
    values = items(4, 10, 18, 22)
    trajectories = TrajectoryManager()
    trajectories.add_move(2, 10, 16, 0.0, 1.0)
    conflict = guard(values, trajectories).conflict_for_move(
        1, 4, 15, 0.0, 11.0, 2.0)
    assert conflict is not None and conflict.neighbor_id == 2


def test_safe_parallel_motion_is_allowed():
    values = items(4, 10, 18, 22)
    trajectories = TrajectoryManager()
    trajectories.add_move(2, 10, 14, 0.0, 1.0)
    assert guard(values, trajectories).is_move_safe(
        manipulator_id=1, start_position=4, end_position=8,
        start_time=0.0, end_time=4.0, required_gap=2.0)


def test_order_reversal_is_conflict():
    assert guard(items(4, 10, 18, 22)).conflict_for_move(
        2, 10, 19, 0.0, 9.0, 2.0) is not None
