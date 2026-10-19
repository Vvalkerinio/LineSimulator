from src.model.manipulator import (
    Manipulator
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

from src.core.transport_assignment_engine import (
    TransportAssignmentEngine
)

from src.core.assignment_selector import (
    AssignmentSelector
)

from src.core.trajectory_manager import (
    TrajectoryManager
)

from src.core.passing_detector import (
    PassingDetector
)


def test_assignment_selector():

    manager = ManipulatorManager(
        [
            Manipulator(
                id=1,
                position=1,
                lift_time=1,
                drop_time=1,
                travel_time_per_position=1
            )
        ]
    )

    engine = (
        TransportAssignmentEngine(
            manager,
            ManipulatorAvailability(),
            TrackReservationService(
                TrackCalendar()
            ),
            TrajectoryManager(),
            PassingDetector(
                TrajectoryManager()
            )
        )
    )

    selector = AssignmentSelector(
        manager,
        ManipulatorAvailability(),
        engine
    )

    assignment = selector.select(
        source_station=5,
        target_station=8,
        current_time=0
    )

    assert assignment is not None