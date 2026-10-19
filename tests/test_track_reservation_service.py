from src.core.track_calendar import (
    TrackCalendar
)

from src.core.track_reservation_service import (
    TrackReservationService
)


def test_can_reserve_track():

    calendar = TrackCalendar()

    service = (
        TrackReservationService(
            calendar
        )
    )

    assert (
        service.can_reserve(
            manipulator_id=1,
            source_station=5,
            target_station=8,
            start_time=0,
            travel_time_per_position=2
        )
        is True
    )