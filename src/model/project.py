from dataclasses import dataclass, field

from src.model.recipe import Recipe
from src.model.bath_group import BathGroup
from src.model.simulation_configuration import (
    SimulationConfiguration
)


@dataclass
class Project:

    name: str

    configuration: SimulationConfiguration

    recipes: list[Recipe] = field(
        default_factory=list
    )

    bath_groups: list[BathGroup] = field(
        default_factory=list
    )

    def add_recipe(
        self,
        recipe: Recipe
    ) -> None:

        self.recipes.append(recipe)

    def add_bath_group(
        self,
        bath_group: BathGroup
    ) -> None:

        self.bath_groups.append(
            bath_group
        )

    def get_bath_group(
        self,
        group_id: str
    ) -> BathGroup:

        for group in self.bath_groups:

            if group.id == group_id:
                return group

        raise KeyError(
            f"Bath group '{group_id}' not found"
        )
