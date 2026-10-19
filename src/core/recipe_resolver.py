from src.model.recipe_step import (
    RecipeStep
)


class RecipeResolver:

    def __init__(
        self,
        bath_group_registry
    ):
        self.bath_group_registry = (
            bath_group_registry
        )

    def resolve_step(
        self,
        step: RecipeStep
    ):

        if (
            step.bath_group_id
            is None
        ):
            return []

        group = (
            self.bath_group_registry.get(
                step.bath_group_id
            )
        )

        return group.stations