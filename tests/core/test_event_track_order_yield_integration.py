from types import SimpleNamespace
from src.core.transport_assignment_engine import TransportAssignmentEngine
from src.core.trajectory_manager import TrajectoryManager
from src.core.manipulator_availability import ManipulatorAvailability

class Manager:
    def __init__(self, items): self.items=items
    def all(self): return self.items
class Track:
    def can_reserve(self, **kwargs): return True

def test_order_failure_populates_conflict_and_plans_right_neighbor_yield():
    items=[
        SimpleNamespace(id=1,position=4,work_zone_start=1,work_zone_end=8,travel_time_per_position=1.0),
        SimpleNamespace(id=2,position=8,work_zone_start=5,work_zone_end=14,travel_time_per_position=1.0),
        SimpleNamespace(id=3,position=15,work_zone_start=14,work_zone_end=19,travel_time_per_position=1.0),
        SimpleNamespace(id=4,position=22,work_zone_start=18,work_zone_end=22,travel_time_per_position=1.0),
    ]
    engine=TransportAssignmentEngine(Manager(items),ManipulatorAvailability(),Track(),TrajectoryManager(),SimpleNamespace())
    engine.minimum_manipulator_spacing=2.0
    assert not engine.validate_order(items[1],14,100.0)
    assert engine.last_track_conflict.neighbor_id == 3
    assert engine.last_track_conflict.side == 'right'
    move=engine.try_plan_yield(14,100.0)
    assert move is not None
    assert move.yielding_manipulator_id == 3
    assert move.end_position == 16
    assert engine.validate_order(items[1],14,move.end_time)
