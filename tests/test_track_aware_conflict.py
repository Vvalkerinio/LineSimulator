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


def test_track_conflict_rejected():

    calendar = TrackCalendar()

    track_service = (
        TrackReservationService(
            calendar
        )
    )

    track_service.reserve(
        manipulator_id=1,
        source_station=5,
        target_station=8,
        start_time=0,
        travel_time_per_position=1
    )

    manager = ManipulatorManager(
        [
            Manipulator(
                id=2,
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
            track_service
        )
    )

    assignment = (
        selector.select(
            source_station=5,
            target_station=8,
            current_time=0
        )
    )

    assert assignment is None