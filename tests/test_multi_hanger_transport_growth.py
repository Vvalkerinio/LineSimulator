from src.model.station import Station
from src.model.manipulator import Manipulator
from src.model.simulation_configuration import (
    SimulationConfiguration
)

from src.core.plant_simulator import (
    PlantSimulator
)


def test_transport_count_grows_with_hangers():

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

    result = PlantSimulator(
        config
    ).run()

    assert (
        len(result.manipulator_tasks)
        > 50
    )