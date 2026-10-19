from src.model.event_type import (
    EventType
)

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


def test_transport_events_exist():

    config = SimulationConfiguration(
        stations=[
            Station(
                id=i,
                name=f"P{i}",
                enabled=True,
                min_process_time=10,
                max_process_time=100
            )
            for i in range(1, 6)
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

    result = (
        EventDrivenSimulator(
            config
        ).run()
    )

    transport_events = [
        e
        for e in result.events
        if e.event_type
        == EventType.TRANSPORT_END
    ]

    assert len(transport_events) > 0