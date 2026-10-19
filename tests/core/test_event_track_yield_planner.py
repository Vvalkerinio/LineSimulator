from types import SimpleNamespace
from src.core.event_track_safety_coordinator import EventTrackConflict, EventTrackSafetyCoordinator
from src.core.event_track_yield_planner import EventTrackYieldPlanner
from src.core.trajectory_manager import TrajectoryManager
from src.core.manipulator_availability import ManipulatorAvailability

class Manager:
    def __init__(self, items): self.items=items
    def all(self): return self.items

def test_idle_right_neighbor_yields_to_release_loaded_path():
    items=[
        SimpleNamespace(id=1,position=4,work_zone_start=1,work_zone_end=8,travel_time_per_position=1.0),
        SimpleNamespace(id=2,position=8,work_zone_start=5,work_zone_end=14,travel_time_per_position=1.0),
        SimpleNamespace(id=3,position=15,work_zone_start=14,work_zone_end=19,travel_time_per_position=1.0),
        SimpleNamespace(id=4,position=22,work_zone_start=18,work_zone_end=22,travel_time_per_position=1.0),
    ]
    manager=Manager(items); trajectories=TrajectoryManager(); availability=ManipulatorAvailability()
    safety=EventTrackSafetyCoordinator(manager,trajectories)
    planner=EventTrackYieldPlanner(manager,availability,trajectories,safety)
    conflict=EventTrackConflict(2,3,0,1,1,2,"right")
    move=planner.plan(conflict,blocked_target=14,current_time=100,required_gap=2)
    assert move is not None
    assert move.yielding_manipulator_id == 3
    assert move.end_position == 16
    assert availability.available_from(3) == 101
    assert items[2].position == 16

def test_yield_is_rejected_when_it_would_hit_outer_neighbor():
    items=[
        SimpleNamespace(id=1,position=4,work_zone_start=1,work_zone_end=8,travel_time_per_position=1.0),
        SimpleNamespace(id=2,position=8,work_zone_start=5,work_zone_end=14,travel_time_per_position=1.0),
        SimpleNamespace(id=3,position=15,work_zone_start=14,work_zone_end=19,travel_time_per_position=1.0),
        SimpleNamespace(id=4,position=17,work_zone_start=16,work_zone_end=22,travel_time_per_position=1.0),
    ]
    manager=Manager(items); trajectories=TrajectoryManager(); availability=ManipulatorAvailability()
    planner=EventTrackYieldPlanner(manager,availability,trajectories,EventTrackSafetyCoordinator(manager,trajectories))
    conflict=EventTrackConflict(2,3,0,1,1,2,"right")
    assert planner.plan(conflict,14,100,2) is None

def test_same_neighbor_can_yield_again_after_previous_move_finished_and_returned():
    items=[
        SimpleNamespace(id=1,position=4,work_zone_start=1,work_zone_end=8,travel_time_per_position=1.0),
        SimpleNamespace(id=2,position=8,work_zone_start=5,work_zone_end=14,travel_time_per_position=1.0),
        SimpleNamespace(id=3,position=15,work_zone_start=14,work_zone_end=19,travel_time_per_position=1.0),
        SimpleNamespace(id=4,position=22,work_zone_start=18,work_zone_end=22,travel_time_per_position=1.0),
    ]
    manager=Manager(items); trajectories=TrajectoryManager(); availability=ManipulatorAvailability()
    planner=EventTrackYieldPlanner(manager,availability,trajectories,EventTrackSafetyCoordinator(manager,trajectories))
    conflict=EventTrackConflict(2,3,100,100,1,2,"right")
    first=planner.plan(conflict,14,100,2)
    assert first is not None and first.end_position == 16
    # A later normal task returned M3 to the blocking position.
    trajectories.add_move(3,16,15,200.0,1.0)
    availability.reserve(3,201.0)
    items[2].position=15
    second=planner.plan(conflict,14,300,2)
    assert second is not None
    assert second.start_position == 15
    assert second.end_position == 16
    assert len(planner.moves) == 2


def test_proposal_has_no_side_effect_until_commit():
    items=[
        SimpleNamespace(id=1,position=4,work_zone_start=1,work_zone_end=8,travel_time_per_position=1.0),
        SimpleNamespace(id=2,position=8,work_zone_start=5,work_zone_end=14,travel_time_per_position=1.0),
        SimpleNamespace(id=3,position=15,work_zone_start=14,work_zone_end=19,travel_time_per_position=1.0),
        SimpleNamespace(id=4,position=22,work_zone_start=18,work_zone_end=22,travel_time_per_position=1.0),
    ]
    manager=Manager(items); trajectories=TrajectoryManager(); availability=ManipulatorAvailability()
    planner=EventTrackYieldPlanner(manager,availability,trajectories,EventTrackSafetyCoordinator(manager,trajectories))
    conflict=EventTrackConflict(2,3,100,100,1,2,"right")
    proposal=planner.propose(conflict,14,100,2)
    assert proposal is not None
    assert items[2].position == 15
    assert availability.available_from(3) == 0.0
    assert planner.moves == []
    planner.commit(proposal)
    assert items[2].position == 16
    assert planner.moves == [proposal]
