from src.core.track_calendar import (
    TrackCalendar
)

from src.model.segment_reservation import (
    SegmentReservation
)


def test_segment_conflict():

    calendar = TrackCalendar()

    calendar.add(
        SegmentReservation(
            manipulator_id=1,
            segment_start=5,
            segment_end=6,
            start_time=0,
            end_time=10
        )
    )

    candidate = (
        SegmentReservation(
            manipulator_id=2,
            segment_start=5,
            segment_end=6,
            start_time=5,
            end_time=15
        )
    )

    assert (
        calendar.has_conflict(
            candidate
        )
        is True
    )