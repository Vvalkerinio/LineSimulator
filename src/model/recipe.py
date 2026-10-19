from dataclasses import dataclass, field

from src.model.recipe_step import (
    RecipeStep
)


@dataclass
class Recipe:

    id: str

    name: str

    steps: list[RecipeStep] = field(
        default_factory=list
    )

    def add_step(
        self,
        step: RecipeStep
    ) -> None:

        self.steps.append(step)

    def step_count(
        self
    ) -> int:

        return len(
            self.steps
        )