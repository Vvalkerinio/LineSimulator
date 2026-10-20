from types import SimpleNamespace

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


def test_yield_proposal_uses_dispatch_time_not_future_availability():
    manipulators = [
        Manipulator(1, 6, 1.0, 1.0, 4.5, 1, 7),
        Manipulator(2, 11, 1.0, 1.0, 4.5, 5, 14),
    ]
    manager = ManipulatorManager(manipulators)
    availability = ManipulatorAvailability()
    availability.reserve(2, 682.0)
    proposal = object()

    class TransportEngine:
        def __init__(self):
            self.yield_times = []

        def position_at(self, manipulator, time_value):
            return manipulator.position

        def validate_order(self, manipulator, target_station, time_value):
            return False

        def propose_yield(self, blocked_target, current_time):
            self.yield_times.append(current_time)
            return proposal

    transport_engine = TransportEngine()
    selector = AssignmentSelector(
        manager,
        availability,
        transport_engine,
    )

    assignment = selector.select(
        source_station=6,
        target_station=8,
        current_time=594.5,
        latest_pickup_time=684.5,
    )

    assert assignment is None
    assert transport_engine.yield_times == [594.5]
    assert selector.consume_pending_yield_proposal() is proposal
