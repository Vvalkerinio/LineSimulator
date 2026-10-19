from src.model.bath_group import (
    BathGroup
)


class BathGroupRegistry:

    def __init__(self):

        self._groups: dict[
            str,
            BathGroup
        ] = {}

    def add(
        self,
        group: BathGroup
    ) -> None:

        self._groups[
            group.id
        ] = group

    def get(
        self,
        group_id: str
    ) -> BathGroup:

        return self._groups[
            group_id
        ]

    def exists(
        self,
        group_id: str
    ) -> bool:

        return (
            group_id
            in self._groups
        )