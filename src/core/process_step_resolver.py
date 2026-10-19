from src.model.process_step_result import (
    ProcessStepResult
)


class ProcessStepResolver:

    def __init__(
        self,
        recipe_resolver
    ):
        self.recipe_resolver = (
            recipe_resolver
        )

    def resolve(
        self,
        recipe_step
    ) -> ProcessStepResult:

        stations = (
            self.recipe_resolver
            .resolve_step(recipe_step)
        )

        return ProcessStepResult(
            step_id=recipe_step.id,
            available_stations=stations
        )