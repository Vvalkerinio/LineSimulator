from src.model.manipulator_assignment import (
    ManipulatorAssignment
)


class TrackAwareSelector:

    def __init__(
        self,
        manipulator_manager,
        availability,
        track_service
    ):
        self.manipulator_manager = (
            manipulator_manager
        )

        self.availability = (
            availability
        )

        self.track_service = (
            track_service
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

            if not (
                self.track_service.can_reserve(
                    manipulator_id=
                        manipulator.id,
                    source_station=
                        source_station,
                    target_station=
                        target_station,
                    start_time=
                        start_time,
                    travel_time_per_position=
                        manipulator.travel_time_per_position
                )
            ):
                continue

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