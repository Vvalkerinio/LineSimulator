from src.model.process_route import (
    ProcessRoute
)


class DynamicRouteBuilder:

    def __init__(
        self,
        process_router
    ):
        self.process_router = (
            process_router
        )

    def build(
        self,
        recipe
    ) -> ProcessRoute:

        route = [1]

        for step in recipe.steps:

            if step.bath_group_id:

                station = (
                    self.process_router
                    .resolve_target_station(
                        step
                    )
                )

                route.append(
                    station
                )

        route.append(22)

        return ProcessRoute(
            stations=route
        )