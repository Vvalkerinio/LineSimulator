from src.core.trajectory_manager import (
    TrajectoryManager
)

from src.core.passing_detector import (
    PassingDetector
)


def test_crossing_detected():

    trajectories = (
        TrajectoryManager()
    )

    trajectories.add_move(
        manipulator_id=1,
        start_position=5,
        end_position=10,
        start_time=0,
        travel_time_per_position=1
    )

    trajectories.add_move(
        manipulator_id=2,
        start_position=10,
        end_position=5,
        start_time=0,
        travel_time_per_position=1
    )

    detector = PassingDetector(
        trajectories
    )

    assert (
        detector.crossing_detected(
            left_manipulator=1,
            right_manipulator=2,
            start_time=0,
            end_time=5
        )
        is True
    )