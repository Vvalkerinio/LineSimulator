from src.model.recipe import Recipe
from src.model.recipe_step import (
    RecipeStep
)
from src.model.bath_group import (
    BathGroup
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


def test_build_route():

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

    route = (
        RouteBuilder(
            RecipeResolver(
                registry
            )
        ).build(recipe)
    )

    assert route.stations == [
        1,
        9,
        22
    ]