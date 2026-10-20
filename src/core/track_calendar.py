from src.model.segment_reservation import (
    SegmentReservation
)


class TrackCalendar:

    def __init__(self):

        self._reservations: list[
            SegmentReservation
        ] = []

    def add(
        self,
        reservation: SegmentReservation
    ) -> None:

        self._reservations.append(
            reservation
        )

    def all(self):

        return self._reservations

    def remove_reservation(self, reservation_id):
        self._reservations = [
            item for item in self._reservations
            if item.reservation_id != reservation_id
        ]

    def has_conflict(
        self,
        reservation: SegmentReservation
    ) -> bool:

        for existing in (
            self._reservations
        ):

            same_segment = (
                existing.segment_start
                ==
                reservation.segment_start
                and
                existing.segment_end
                ==
                reservation.segment_end
            )

            if not same_segment:
                continue

            overlap = not (
                reservation.end_time
                <= existing.start_time
                or
                reservation.start_time
                >= existing.end_time
            )

            if overlap:
                return True

        return False