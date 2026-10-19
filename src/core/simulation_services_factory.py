from src.model.simulation_services import (
    SimulationServices
)

from src.core.manipulator_manager import (
    ManipulatorManager
)

from src.core.manipulator_availability import (
    ManipulatorAvailability
)

from src.core.track_calendar import (
    TrackCalendar
)

from src.core.track_reservation_service import (
    TrackReservationService
)

from src.core.trajectory_manager import (
    TrajectoryManager
)

from src.core.passing_detector import (
    PassingDetector
)

from src.core.transport_assignment_engine import (
    TransportAssignmentEngine
)

from src.core.assignment_selector import (
    AssignmentSelector
)

from src.core.transport_scheduler import (
    TransportScheduler
)


class SimulationServicesFactory:

    @staticmethod
    def create(
        manipulators,
        stations=None
    ) -> SimulationServices:

        manipulator_manager = (
            ManipulatorManager(
                manipulators
            )
        )

        availability = (
            ManipulatorAvailability()
        )

        track_calendar = (
            TrackCalendar()
        )

        track_service = (
            TrackReservationService(
                track_calendar
            )
        )

        trajectory_manager = (
            TrajectoryManager()
        )

        passing_detector = (
            PassingDetector(
                trajectory_manager
            )
        )

        transport_engine = (
            TransportAssignmentEngine(
                manipulator_manager=
                    manipulator_manager,
                availability=
                    availability,
                track_service=
                    track_service,
                trajectory_manager=
                    trajectory_manager,
                passing_detector=
                    passing_detector
            )
        )

        selector = (
            AssignmentSelector(
                manipulator_manager=
                    manipulator_manager,
                availability=
                    availability,
                transport_engine=
                    transport_engine,
                stations=stations
            )
        )

        scheduler = (
            TransportScheduler(
                selector
            )
        )

        return SimulationServices(
            transport_scheduler=
                scheduler,

            manipulator_manager=
                manipulator_manager,

            availability=
                availability,

            track_service=
                track_service,

            trajectory_manager=
                trajectory_manager
        )