from src.model.manipulator_assignment import (
    ManipulatorAssignment
)


class ManipulatorSelector:

    def __init__(
        self,
        manipulator_manager,
        availability
    ):
        self.manipulator_manager = (
            manipulator_manager
        )

        self.availability = (
            availability
        )

    def select(
        self,
        source_station: int,
        target_station: int,
        current_time: float
    ) -> ManipulatorAssignment:

        best_assignment = None

        for manipulator in (
            self.manipulator_manager.all()
        ):

            start_time = max(
                current_time,
                self.availability.available_from(
                    manipulator.id
                )
            )

            travel_time = (
                manipulator.transport_time(
                    source_station,
                    target_station
                )
            )

            finish_time = (
                start_time
                + manipulator.lift_time
                + travel_time
                + manipulator.drop_time
            )

            assignment = (
                ManipulatorAssignment(
                    manipulator_id=
                        manipulator.id,

                    source_station=
                        source_station,

                    target_station=
                        target_station,

                    start_time=
                        start_time,

                    finish_time=
                        finish_time
                )
            )

            if (
                best_assignment is None
                or
                assignment.finish_time
                < best_assignment.finish_time
            ):
                best_assignment = assignment

        if best_assignment is None:
            return None

        self.availability.reserve(
            best_assignment.manipulator_id,
            best_assignment.finish_time
        )

        return best_assignment