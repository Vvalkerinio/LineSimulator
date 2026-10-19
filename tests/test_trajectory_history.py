from src.core.trajectory_manager import (
    TrajectoryManager
)


def test_history_kept():

    manager = (
        TrajectoryManager()
    )

    manager.add_move(
        manipulator_id=1,
        start_position=1,
        end_position=5,
        start_time=0,
        travel_time_per_position=1
    )

    manager.add_move(
        manipulator_id=1,
        start_position=5,
        end_position=10,
        start_time=10,
        travel_time_per_position=1
    )

    segments = (
        manager.segments_for(1)
    )

    assert len(segments) == 2