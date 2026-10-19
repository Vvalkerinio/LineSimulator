from main import config

from src.core.plant_simulator import (
    PlantSimulator
)


def test_simulation():

    simulator = PlantSimulator(
        config
    )

    result = simulator.run()

    assert len(result.events) > 0