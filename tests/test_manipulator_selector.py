from src.model.manipulator import (
    Manipulator
)

from src.core.manipulator_manager import (
    ManipulatorManager
)

from src.core.manipulator_selector import (
    ManipulatorSelector
)

from src.core.manipulator_availability import (
    ManipulatorAvailability
)


def test_select_fastest_manipulator():

    manager = ManipulatorManager(
        [
            Manipulator(
                id=1,
                position=1,
                lift_time=10,
                drop_time=10,
                travel_time_per_position=5
            ),
            Manipulator(
                id=2,
                position=1,
                lift_time=2,
                drop_time=2,
                travel_time_per_position=1
            )
        ]
    )

    selector = ManipulatorSelector(
        manager,
        ManipulatorAvailability()
    )

    assignment = selector.select(
        source_station=1,
        target_station=5,
        current_time=0
    )

    assert (
        assignment.manipulator_id
        == 2
    )