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

from src.core.trajectory_manager import (
    TrajectoryManager
)

from src.core.passing_detector import (
    PassingDetector
)


def test_track_validation():

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

    manipulator = (
        manager.get(1)
    )

    assert (
        engine.validate_track(
            manipulator,
            5,
            8,
            0
        )
        is True
    )