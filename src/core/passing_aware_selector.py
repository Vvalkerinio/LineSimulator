from src.model.manipulator_assignment import (
    ManipulatorAssignment
)


class PassingAwareSelector:

    def __init__(
        self,
        manipulator_manager,
        availability,
        trajectory_manager,
        passing_detector
    ):
        self.manipulator_manager = (
            manipulator_manager
        )

        self.availability = (
            availability
        )

        self.trajectory_manager = (
            trajectory_manager
        )

        self.passing_detector = (
            passing_detector
        )

    def select(
        self,
        source_station: int,
        target_station: int,
        current_time: float
    ):

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
                manipulator.travel_time(
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

            conflict = False

            for other in (
                self.manipulator_manager.all()
            ):

                if other.id == manipulator.id:
                    continue

                try:
                    crossing = (
                        self.passing_detector
                        .crossing_detected(
                            manipulator.id,
                            other.id,
                            start_time,
                            finish_time
                        )
                    )

                    if crossing:
                        conflict = True
                        break

                except KeyError:
                    pass

            if conflict:
                continue

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

        return best_assignment