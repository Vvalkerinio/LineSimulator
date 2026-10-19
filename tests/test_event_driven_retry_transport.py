from src.model.simulation_configuration import (
    SimulationConfiguration
)

from src.model.station import (
    Station
)

from src.model.manipulator import (
    Manipulator
)

from src.core.event_driven_simulator import (
    EventDrivenSimulator
)


def test_retry_event_exists():

    config = SimulationConfiguration(
        stations=[
            Station(
                id=i,
                name=f"P{i}",
                enabled=True,
                min_process_time=10,
                max_process_time=100
            )
            for i in range(1, 4)
        ],
        manipulators=[
            Manipulator(
                id=1,
                position=1,
                lift_time=1,
                drop_time=1,
                travel_time_per_position=1
            )
        ]
    )

    config.hanger_count = 2

    result = (
        EventDrivenSimulator(
            config
        ).run()
    )

    assert len(result.events) > 0