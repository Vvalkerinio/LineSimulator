class ManipulatorAvailability:

    def __init__(self):

        self._busy_until: dict[
            int,
            float
        ] = {}

    def available_from(
        self,
        manipulator_id: int
    ) -> float:

        return self._busy_until.get(
            manipulator_id,
            0.0
        )

    def reserve(
        self,
        manipulator_id: int,
        finish_time: float
    ) -> None:

        self._busy_until[
            manipulator_id
        ] = finish_time