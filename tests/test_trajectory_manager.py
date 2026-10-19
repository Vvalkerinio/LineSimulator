from src.core.trajectory_manager import (
    TrajectoryManager
)


def test_interpolated_position():

    manager = (
        TrajectoryManager()
    )

    manager.add_move(
        manipulator_id=1,
        start_position=5,
        end_position=7,
        start_time=0,
        travel_time_per_position=2
    )

    position = (
        manager.position_at(
            manipulator_id=1,
            time_value=1
        )
    )

    assert position == 5.5