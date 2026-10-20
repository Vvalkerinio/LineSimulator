from src.core.segment_builder import (
    SegmentBuilder
)


class TrackReservationService:

    def __init__(
        self,
        track_calendar
    ):
        self.track_calendar = (
            track_calendar
        )

        self.segment_builder = (
            SegmentBuilder()
        )

    def can_reserve(
        self,
        manipulator_id: int,
        source_station: int,
        target_station: int,
        start_time: float,
        travel_time_per_position: float
    ) -> bool:

        reservations = (
            self.segment_builder.build(
                manipulator_id=
                    manipulator_id,

                source_station=
                    source_station,

                target_station=
                    target_station,

                start_time=
                    start_time,

                travel_time_per_position=
                    travel_time_per_position
            )
        )

        for reservation in reservations:

            if (
                self.track_calendar
                .has_conflict(
                    reservation
                )
            ):
                return False

        return True

    def reserve(
        self,
        manipulator_id: int,
        source_station: int,
        target_station: int,
        start_time: float,
        travel_time_per_position: float,
        reservation_id=None,
    ) -> None:

        reservations = (
            self.segment_builder.build(
                manipulator_id=
                    manipulator_id,

                source_station=
                    source_station,

                target_station=
                    target_station,

                start_time=
                    start_time,

                travel_time_per_position=
                    travel_time_per_position
            )
        )

        for reservation in reservations:
            reservation.reservation_id = reservation_id
            self.track_calendar.add(
                reservation
            )

    def cancel_reservation(self, reservation_id):
        self.track_calendar.remove_reservation(reservation_id)