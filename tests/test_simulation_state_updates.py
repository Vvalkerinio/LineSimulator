from src.model.station import Station
from src.model.manipulator import (
    Manipulator
)

from src.model.simulation_configuration import (
    SimulationConfiguration
)

from src.core.plant_simulator import (
    PlantSimulator
)


def test_simulator_updates_state():

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

    result = PlantSimulator(
        config
    ).run()

    assert result.processed_events > 0

    assert result.final_time > 0