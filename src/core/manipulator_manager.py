from src.model.manipulator import (
    Manipulator
)


class ManipulatorManager:

    def __init__(
        self,
        manipulators: list[Manipulator]
    ):
        self._manipulators = {
            m.id: m
            for m in manipulators
        }

    def get(
        self,
        manipulator_id: int
    ) -> Manipulator:

        return self._manipulators[
            manipulator_id
        ]

    def all(self):

        return list(
            self._manipulators.values()
        )

    def count(self) -> int:

        return len(
            self._manipulators
        )

    def sorted_by_position(
        self
    ):

        return sorted(
            self._manipulators.values(),
            key=lambda m: m.position
        )