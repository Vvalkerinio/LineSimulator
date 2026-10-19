from src.model.recipe import Recipe
from src.model.recipe_step import (
    RecipeStep
)


def test_recipe_step_count():

    recipe = Recipe(
        id="TEST",
        name="Test Recipe"
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
            name="Shared Bath",
            min_time=30,
            max_time=60,
            bath_group_id="KTL_1"
        )
    )

    assert recipe.step_count() == 2