from dataclasses import (
    dataclass,
    field
)

from src.model.manipulator_program_step import (
    ManipulatorProgramStep
)


@dataclass
class ManipulatorProgram:

    manipulator_id: int

    index_address: int

    station_offset: int = 0

    station_id_shift: int = 1

    max_program_words: int = 99

    steps: list[ManipulatorProgramStep] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    def program_start_address(
        self
    ):
        return (
            self.index_address
            +
            1
        )

    def words(
        self
    ):
        result = []

        for step in self.steps:
            result.extend(
                step.words()
            )

        if len(
            result
        ) > self.max_program_words:
            self.warnings.append(
                (
                    f"Manipulator M{self.manipulator_id}: "
                    f"program ma {len(result)} WORD, "
                    f"limit wynosi {self.max_program_words}. "
                    f"Program zostanie ucięty."
                )
            )

            result = result[
                :self.max_program_words
            ]

        while len(
            result
        ) < self.max_program_words:
            result.append(
                0
            )

        return result

    def logical_step_count(
        self
    ):
        return len(
            self.steps
        )

    def max_logical_steps(
        self
    ):
        return (
            self.max_program_words
            //
            3
        )

    def word_count_used(
        self
    ):
        return min(
            len(
                self.steps
            )
            *
            3,
            self.max_program_words
        )