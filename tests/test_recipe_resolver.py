from src.model.bath_group import (
    BathGroup
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


def test_resolve_shared_bath():

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

    step = RecipeStep(
        id="KTL_1",
        name="Shared Bath",
        min_time=10,
        max_time=300,
        bath_group_id="KTL_1"
    )

    stations = (
        resolver.resolve_step(
            step
        )
    )

    assert stations == [9, 10]