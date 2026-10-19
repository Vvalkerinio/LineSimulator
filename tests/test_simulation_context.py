from src.model.recipe import Recipe
from src.model.simulation_context import (
    SimulationContext
)


def test_context_holds_recipe():

    recipe = Recipe(
        id="TEST",
        name="Recipe"
    )

    context = SimulationContext(
        recipe=recipe
    )

    assert (
        context.recipe.id
        == "TEST"
    )