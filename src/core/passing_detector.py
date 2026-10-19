class PassingDetector:

    SAFETY_DISTANCE = 0.1

    def __init__(
        self,
        trajectory_manager
    ):
        self.trajectory_manager = (
            trajectory_manager
        )

    def crossing_detected(
        self,
        left_manipulator: int,
        right_manipulator: int,
        start_time: float,
        end_time: float,
        step: float = 0.25
    ) -> bool:

        current_time = start_time

        while current_time <= end_time:

            left_position = (
                self.trajectory_manager.position_at(
                    left_manipulator,
                    current_time
                )
            )

            right_position = (
                self.trajectory_manager.position_at(
                    right_manipulator,
                    current_time
                )
            )

            if (
                right_position
                - left_position
                <= self.SAFETY_DISTANCE
            ):
                return True

            current_time += step

        return False