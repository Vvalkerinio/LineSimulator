from src.model.process_route import (
    ProcessRoute
)


class RouteBuilder:

    def __init__(
        self,
        recipe_resolver
    ):
        self.recipe_resolver = (
            recipe_resolver
        )

    def build(
        self,
        recipe
    ) -> ProcessRoute:

        route = [1]

        for step in recipe.steps:

            stations = (
                self.recipe_resolver
                .resolve_step(step)
            )

            if not stations:
                continue

            route.append(
                stations[0]
            )

        route.append(22)

        return ProcessRoute(
            stations=route
        )