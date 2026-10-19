from dataclasses import dataclass


@dataclass
class RecipeStep:

    id: str

    name: str

    min_time: float

    max_time: float

    bath_group_id: str | None = None