from src.model.bath_group import (
    BathGroup
)
from src.model.recipe import (
    Recipe
)
from src.model.recipe_step import (
    RecipeStep
)

from src.core.bath_group_registry import (
    BathGroupRegistry
)
from src.core.recipe_resolver import (
    RecipeResolver
)


def test_recipe_flow():

    recipe = Recipe(
        id="TEST",
        name="Test Recipe"
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

    registry = (
        BathGroupRegistry()
    )

    registry.add(
        BathGroup(
            id="KTL_1",
            name="Shared Bath",
            stations=[9, 10]
        )
    )

    resolver = (
        RecipeResolver(
            registry
        )
    )

    stations = (
        resolver.resolve_step(
            recipe.steps[0]
        )
    )

    assert stations == [9, 10]