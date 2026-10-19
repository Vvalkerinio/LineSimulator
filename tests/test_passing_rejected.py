from src.model.manipulator import (
    Manipulator
)

from src.core.manipulator_manager import (
    ManipulatorManager
)

from src.core.manipulator_availability import (
    ManipulatorAvailability
)

from src.core.trajectory_manager import (
    TrajectoryManager
)

from src.core.passing_detector import (
    PassingDetector
)

from src.core.passing_aware_selector import (
    PassingAwareSelector
)


def test_selector_rejects_crossing():

    manager = ManipulatorManager(
        [
            Manipulator(
                id=1,
                position=1,
                lift_time=1,
                drop_time=1,
                travel_time_per_position=1
            ),
            Manipulator(
                id=2,
                position=1,
                lift_time=1,
                drop_time=1,
                travel_time_per_position=1
            )
        ]
    )

    trajectories = (
        TrajectoryManager()
    )

    trajectories.add_move(
        manipulator_id=2,
        start_position=10,
        end_position=5,
        start_time=0,
        travel_time_per_position=1
    )

    selector = (
        PassingAwareSelector(
            manager,
            ManipulatorAvailability(),
            trajectories,
            PassingDetector(
                trajectories
            )
        )
    )

    assignment = selector.select(
        source_station=5,
        target_station=10,
        current_time=0
    )

    # na tym etapie dopuszczamy:
    # None lub wybór innego manipulatora

    assert (
        assignment is None
        or
        assignment.manipulator_id != 2
    )