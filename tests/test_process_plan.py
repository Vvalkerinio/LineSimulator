from src.model.recipe import Recipe
from src.model.recipe_step import (
    RecipeStep
)

from src.core.recipe_route_builder import (
    RecipeRouteBuilder
)


def test_process_plan():

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

    plan = (
        RecipeRouteBuilder()
        .build(recipe)
    )

    assert len(plan.nodes) == 1

    assert (
        plan.nodes[0].is_bath_group
        is True
    )
