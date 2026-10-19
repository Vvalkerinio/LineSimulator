from src.model.recipe import Recipe
from src.model.recipe_step import (
    RecipeStep
)

from src.model.bath_group import (
    BathGroup
)

from src.model.station import Station
from src.model.manipulator import (
    Manipulator
)

from src.model.simulation_configuration import (
    SimulationConfiguration
)

from src.model.simulation_context import (
    SimulationContext
)

from src.core.bath_group_registry import (
    BathGroupRegistry
)

from src.core.recipe_resolver import (
    RecipeResolver
)

from src.core.route_builder import (
    RouteBuilder
)

from src.core.plant_simulator import (
    PlantSimulator
)


def test_recipe_route_in_simulator():

    recipe = Recipe(
        id="TEST",
        name="Recipe"
    )

    recipe.add_step(
        RecipeStep(
            id="KTL_1",
            name="Shared Bath",
            min_time=10,
            max_time=300,
            bath_group_id="KTL_1"
        )
    )

    registry = (
        BathGroupRegistry()
    )

    registry.add(
        BathGroup(
            id="KTL_1",
            name="Bath",
            stations=[9, 10]
        )
    )

    config = (
        SimulationConfiguration(
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
                    lift_time=3,
                    drop_time=3,
                    travel_time_per_position=2
                )
            ]
        )
    )

    simulator = PlantSimulator(
        config=config,
        context=SimulationContext(
            recipe=recipe
        ),
        route_builder=
            RouteBuilder(
                RecipeResolver(
                    registry
                )
            )
    )

    result = simulator.run()

    assert len(result.events) == 2