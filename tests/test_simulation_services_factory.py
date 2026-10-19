from src.model.manipulator import (
    Manipulator
)

from src.core.simulation_services_factory import (
    SimulationServicesFactory
)


def test_factory_creates_scheduler():

    services = (
        SimulationServicesFactory.create(
            [
                Manipulator(
                    id=1,
                    position=1,
                    lift_time=3,
                    drop_time=3,
                    travel_time_per_position=2
                )
            ]
        )
    )

    assert (
        services.transport_scheduler
        is not None
    )

    assert (
        services.manipulator_manager
        is not None
    )

    assert (
        services.availability
        is not None
    )

    assert (
        services.track_service
        is not None
    )

    assert (
        services.trajectory_manager
        is not None
    )