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


def test_yield_uses_request_time_not_busy_manipulator_candidate_time():
    manager = ManipulatorManager(
        [
            Manipulator(1, 6, 1, 1, 1, 1, 6),
            Manipulator(2, 8, 1, 1, 1, 6, 8),
        ]
    )
    availability = ManipulatorAvailability()
    availability.reserve(1, 20.0)
    availability.reserve(2, 100.0)

    class AlwaysBlockedEngine:
        def __init__(self):
            self.yield_request_times = []
            self.proposal = object()

        def position_at(self, manipulator, _time):
            return manipulator.position

        def validate_order(self, _manipulator, _target, _time):
            return True

        def validate_assignment_track(self, **_kwargs):
            return False

        def propose_yield(self, blocked_target, current_time):
            self.yield_request_times.append((blocked_target, current_time))
            return self.proposal

    engine = AlwaysBlockedEngine()
    selector = AssignmentSelector(manager, availability, engine)

    assignment = selector.select(
        source_station=6,
        target_station=8,
        current_time=20.0,
    )

    assert assignment is None
    assert engine.yield_request_times == [(6, 20.0)]
    assert selector.consume_pending_yield_proposal() is engine.proposal