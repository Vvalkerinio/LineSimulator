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


def test_busy_manipulator_not_selected():

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
                lift_time=2,
                drop_time=2,
                travel_time_per_position=2
            )
        ]
    )

    availability = (
        ManipulatorAvailability()
    )

    availability.reserve(
        manipulator_id=1,
        finish_time=100
    )

    selector = (
        ManipulatorSelector(
            manager,
            availability
        )
    )

    assignment = (
        selector.select(
            source_station=1,
            target_station=2,
            current_time=0
        )
    )

    assert (
        assignment.manipulator_id
        == 2
    )


def test_provisional_reservation_conflicts_only_with_overlapping_work():
    availability = ManipulatorAvailability()
    availability.reserve_provisional(
        reservation_id="future-task",
        manipulator_id=1,
        start_time=10.0,
        finish_time=20.0,
    )

    assert availability.available_from(1) == 0.0
    assert not availability.has_conflicting_reservation(1, 0.0, 10.0)
    assert availability.has_conflicting_reservation(1, 9.0, 11.0)
    assert availability.conflicting_reservation_end(1, 9.0, 11.0) == 20.0