class ManipulatorAvailability:

    def __init__(self):

        self._busy_until: dict[
            int,
            float
        ] = {}
        self._provisional: dict[object, tuple[int, float, float]] = {}

    def available_from(
        self,
        manipulator_id: int
    ) -> float:

        return self._busy_until.get(manipulator_id, 0.0)

    def reserve_provisional(
        self,
        reservation_id: object,
        manipulator_id: int,
        start_time: float,
        finish_time: float,
    ) -> None:
        self._provisional[reservation_id] = (
            int(manipulator_id),
            float(start_time),
            float(finish_time),
        )

    def cancel_provisional(self, reservation_id: object) -> None:
        self._provisional.pop(reservation_id, None)

    def has_conflicting_reservation(
        self,
        manipulator_id: int,
        start_time: float,
        finish_time: float,
        excluding: object | None = None,
    ) -> bool:
        if self._busy_until.get(int(manipulator_id), 0.0) > float(start_time):
            return True
        return any(
            reserved_id != excluding
            and reserved_manipulator_id == int(manipulator_id)
            and float(start_time) < reserved_finish
            and float(finish_time) > reserved_start
            for reserved_id, (
                reserved_manipulator_id,
                reserved_start,
                reserved_finish,
            ) in self._provisional.items()
        )

    def conflicting_reservation_end(
        self,
        manipulator_id: int,
        start_time: float,
        finish_time: float,
    ) -> float | None:
        conflicts = [
            reserved_finish
            for reserved_manipulator_id, reserved_start, reserved_finish
            in self._provisional.values()
            if reserved_manipulator_id == int(manipulator_id)
            and float(start_time) < reserved_finish
            and float(finish_time) > reserved_start
        ]
        return min(conflicts, default=None)

    def reserve(
        self,
        manipulator_id: int,
        finish_time: float
    ) -> None:

        self._busy_until[
            manipulator_id
        ] = finish_time