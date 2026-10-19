from types import SimpleNamespace

from src.core.event_track_safety_coordinator import EventTrackConflict, EventTrackSafetyCoordinator
from src.core.event_track_yield_planner import EventTrackYieldPlanner
from src.core.manipulator_availability import ManipulatorAvailability
from src.core.trajectory_manager import TrajectoryManager

class Manager:
    def __init__(self, items): self.items = items
    def all(self): return self.items

def make_planner():
    items = [
        SimpleNamespace(id=1, position=4, work_zone_start=1, work_zone_end=8, travel_time_per_position=1.0),
        SimpleNamespace(id=2, position=8, work_zone_start=5, work_zone_end=14, travel_time_per_position=1.0),
        SimpleNamespace(id=3, position=15, work_zone_start=14, work_zone_end=19, travel_time_per_position=1.0),
        SimpleNamespace(id=4, position=22, work_zone_start=18, work_zone_end=22, travel_time_per_position=1.0),
    ]
    manager = Manager(items)
    trajectories = TrajectoryManager()
    availability = ManipulatorAvailability()
    planner = EventTrackYieldPlanner(
        manager, availability, trajectories,
        EventTrackSafetyCoordinator(manager, trajectories)
    )
    return planner, items, trajectories, availability

def test_proposal_has_no_side_effects():
    planner, items, trajectories, availability = make_planner()
    conflict = EventTrackConflict(2, 3, 100, 100, 1, 2, "right")
    proposal = planner.propose(conflict, 14, 100, 2)
    assert proposal is not None
    assert items[2].position == 15
    assert trajectories.segments_for(3) == []
    assert availability.available_from(3) == 0.0
    assert planner.moves == []

def test_same_neighbor_can_yield_again_after_previous_yield_expired_and_returned():
    planner, items, trajectories, _ = make_planner()
    conflict = EventTrackConflict(2, 3, 100, 100, 1, 2, "right")
    first = planner.commit(planner.propose(conflict, 14, 100, 2))
    assert first.end_position == 16
    # A later normal task returns M3 to ST15.
    trajectories.add_move(3, 16, 15, 150, 1.0)
    items[2].position = 15
    second = planner.propose(conflict, 14, 200, 2)
    assert second is not None
    assert second.start_position == 15
    assert second.end_position == 16
