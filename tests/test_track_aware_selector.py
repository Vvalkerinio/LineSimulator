from src.model.manipulator import (
    Manipulator
)

from src.core.manipulator_manager import (
    ManipulatorManager
)

from src.core.manipulator_availability import (
    ManipulatorAvailability
)

from src.core.track_calendar import (
    TrackCalendar
)

from src.core.track_reservation_service import (
    TrackReservationService
)

from src.core.track_aware_selector import (
    TrackAwareSelector
)


def test_track_aware_assignment():

    manager = ManipulatorManager(
        [
            Manipulator(
                id=1,
                position=1,
                lift_time=1,
                drop_time=1,
                travel_time_per_position=1
            )
        ]
    )

    selector = (
        TrackAwareSelector(
            manager,
            ManipulatorAvailability(),
            TrackReservationService(
                TrackCalendar()
            )
        )
    )

    assignment = (
        selector.select(
            source_station=5,
            target_station=8,
            current_time=0
        )
    )

    assert assignment is not None