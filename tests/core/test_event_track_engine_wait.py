from types import SimpleNamespace

from src.core.transport_assignment_engine import TransportAssignmentEngine
from src.core.trajectory_manager import TrajectoryManager


class Manager:
    def __init__(self, items): self.items = items
    def all(self): return self.items


class AlwaysFreeTrack:
    def can_reserve(self, **kwargs): return True


def test_conflicting_attempt_is_rejected_and_later_attempt_is_allowed():
    m1 = SimpleNamespace(id=1, position=4, travel_time_per_position=1.0)
    m2 = SimpleNamespace(id=2, position=10, travel_time_per_position=1.0)
    m3 = SimpleNamespace(id=3, position=18, travel_time_per_position=1.0)
    m4 = SimpleNamespace(id=4, position=22, travel_time_per_position=1.0)
    trajectories = TrajectoryManager()
    trajectories.add_move(2, 10, 16, 0.0, 1.0)
    engine = TransportAssignmentEngine(
        Manager([m1, m2, m3, m4]), SimpleNamespace(), AlwaysFreeTrack(),
        trajectories, SimpleNamespace()
    )
    engine.minimum_manipulator_spacing = 2.0
    assert engine._path_blocked_by_other_manipulator(m1, 4, 15, 0, 11)
    assert engine.prevented_track_conflicts
    # After M2 completed and is at 16, M1 can safely stop at 14.
    assert not engine._path_blocked_by_other_manipulator(m1, 4, 14, 20, 30)
