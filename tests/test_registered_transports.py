from src.model.station import Station
from src.model.manipulator import (
    Manipulator
)

from src.model.simulation_configuration import (
    SimulationConfiguration
)

from src.model.simulation_services import (
    SimulationServices
)

from src.core.plant_simulator import (
    PlantSimulator
)

from src.core.transport_scheduler import (
    TransportScheduler
)

from src.core.assignment_selector import (
    AssignmentSelector
)

from src.core.transport_assignment_engine import (
    TransportAssignmentEngine
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


def test_scheduler_creates_transports():

    manipulators = [
        Manipulator(
            id=1,
            position=1,
            lift_time=1,
            drop_time=1,
            travel_time_per_position=1
        )
    ]

    manager = ManipulatorManager(
        manipulators
    )

    scheduler = TransportScheduler(
        AssignmentSelector(
            manager,
            ManipulatorAvailability(),
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
    )

    simulator = PlantSimulator(
        config=SimulationConfiguration(
            stations=[
                Station(
                    id=i,
                    name=f"P{i}",
                    enabled=True,
                    min_process_time=10,
                    max_process_time=300
                )
                for i in range(1, 23)
            ],
            manipulators=manipulators
        ),
        services=SimulationServices(
            transport_scheduler=scheduler
        )
    )

    result = simulator.run()

    assert result.processed_events > 0