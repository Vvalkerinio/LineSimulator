from src.model.recipe import Recipe
from src.model.recipe_step import (
    RecipeStep
)

from src.core.recipe_route_builder import (
    RecipeRouteBuilder
)


def test_build_recipe_route():

    recipe = Recipe(
        id="TEST",
        name="Recipe"
    )

    recipe.add_step(
        RecipeStep(
            id="P2",
            name="Station 2",
            min_time=10,
            max_time=300
        )
    )

    recipe.add_step(
        RecipeStep(
            id="KTL_1",
            name="Bath",
            min_time=10,
            max_time=300,
            bath_group_id="KTL_1"
        )
    )

    plan = (
        RecipeRouteBuilder()
        .build(recipe)
    )

    assert len(plan.nodes) == 2

    assert plan.nodes[0].node_id == "P2"

    assert plan.nodes[1].node_id == "KTL_1"

    assert plan.nodes[1].is_bath_group is True