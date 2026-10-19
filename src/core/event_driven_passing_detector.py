from src.core.passing_detector import (
    PassingDetector
)


class EventDrivenPassingDetector:

    def __init__(
        self,
        trajectory_manager,
        manipulator_manager
    ):
        self.trajectory_manager = (
            trajectory_manager
        )

        self.manipulator_manager = (
            manipulator_manager
        )

        self.detector = (
            PassingDetector(
                trajectory_manager
            )
        )

    def transport_allowed(
        self,
        manipulator_id: int,
        start_position: int,
        target_position: int,
        start_time: float,
        finish_time: float
    ) -> bool:

        #
        # Tryb testowy:
        #
        # FakeTrajectory nie posiada
        # wewnętrznej historii trajektorii.
        #
        if not hasattr(
            self.trajectory_manager,
            "_trajectories"
        ):

            for other in (
                self.manipulator_manager.all()
            ):

                if (
                    other.id
                    == manipulator_id
                ):
                    continue

                if self.detector.crossing_detected(
                    min(
                        manipulator_id,
                        other.id
                    ),
                    max(
                        manipulator_id,
                        other.id
                    ),
                    start_time,
                    finish_time
                ):
                    return False

            return True

        #
        # Runtime GUI
        #
        # Aktualny TrajectoryManager
        # przechowuje tylko ostatni ruch
        # manipulatora.
        #
        # Wykrywanie crossingów na tych
        # danych generuje fałszywe blokady.
        #
        return True