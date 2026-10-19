from src.model.recipe_step import (
    RecipeStep
)


class ProcessRouter:

    def __init__(
        self,
        recipe_resolver,
        routing_engine
    ):
        self.recipe_resolver = (
            recipe_resolver
        )

        self.routing_engine = (
            routing_engine
        )

    def resolve_target_station(
        self,
        step: RecipeStep
    ) -> int:

        stations = (
            self.recipe_resolver
            .resolve_step(step)
        )

        decision = (
            self.routing_engine
            .select_station(
                stations
            )
        )

        return (
            decision.selected_station
        )