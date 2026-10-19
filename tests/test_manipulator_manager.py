from src.model.manipulator import (
    Manipulator
)

from src.core.manipulator_manager import (
    ManipulatorManager
)


def test_manipulator_count():

    manager = ManipulatorManager(
        [
            Manipulator(
                id=1,
                position=1,
                lift_time=3,
                drop_time=3,
                travel_time_per_position=2
            ),
            Manipulator(
                id=2,
                position=5,
                lift_time=3,
                drop_time=3,
                travel_time_per_position=2
            )
        ]
    )

    assert manager.count() == 2