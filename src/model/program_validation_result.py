from dataclasses import (
    dataclass,
    field
)


@dataclass
class ProgramValidationMessage:

    manipulator_id: int

    level: str

    code: str

    message: str


@dataclass
class ProgramValidationResult:

    valid: bool = True

    messages: list[
        ProgramValidationMessage
    ] = field(
        default_factory=list
    )

    def add_error(
        self,
        manipulator_id,
        code,
        message
    ):
        self.valid = False

        self.messages.append(
            ProgramValidationMessage(
                manipulator_id=(
                    manipulator_id
                ),
                level="ERROR",
                code=code,
                message=message
            )
        )

    def add_warning(
        self,
        manipulator_id,
        code,
        message
    ):
        self.messages.append(
            ProgramValidationMessage(
                manipulator_id=(
                    manipulator_id
                ),
                level="WARNING",
                code=code,
                message=message
            )
        )

    def add_info(
        self,
        manipulator_id,
        code,
        message
    ):
        self.messages.append(
            ProgramValidationMessage(
                manipulator_id=(
                    manipulator_id
                ),
                level="INFO",
                code=code,
                message=message
            )
        )