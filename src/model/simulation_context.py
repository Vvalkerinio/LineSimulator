from dataclasses import dataclass

from src.model.recipe import Recipe


@dataclass
class SimulationContext:

    recipe: Recipe | None = None
