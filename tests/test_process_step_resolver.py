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

from src.core.process_step_resolver import (
    ProcessStepResolver
)


def test_resolve_step():

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
        ProcessStepResolver(
            RecipeResolver(
                registry
            )
        )
    )

    result = resolver.resolve(
        RecipeStep(
            id="KTL_1",
            name="Shared Bath",
            min_time=10,
            max_time=300,
            bath_group_id="KTL_1"
        )
    )

    assert result.step_id == "KTL_1"

    assert result.available_stations == [
        9,
        10
    ]