from src.model.station import (
    Station
)

from src.model.manipulator import (
    Manipulator
)

from src.model.simulation_configuration import (
    SimulationConfiguration
)

from src.core.event_driven_simulator import (
    EventDrivenSimulator
)


def test_event_driven_simulator_creates_events():

    config = SimulationConfiguration(
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

    config.hanger_count = 5

    result = (
        EventDrivenSimulator(
            config
        ).run()
    )

    assert (
        result.generated_hangers
        == 5
    )

    assert (
        len(result.events)
        > 0
    )
