from src.model.program_validation_result import (
    ProgramValidationResult
)


class ProgramValidator:

    ACTION_PICKUP = 1
    ACTION_DROP = 2

    def validate(
        self,
        programs
    ):
        result = (
            ProgramValidationResult()
        )

        for manipulator_id in sorted(
            programs.keys()
        ):
            self._validate_program(
                manipulator_id,
                programs[
                    manipulator_id
                ],
                result
            )

        return result

    def _validate_program(
        self,
        manipulator_id,
        program,
        result
    ):
        steps = (
            program.steps
        )

        if not steps:
            result.add_error(
                manipulator_id,
                "EMPTY_PROGRAM",
                "Program nie zawiera żadnych kroków."
            )
            return

        self._check_step_limit(
            manipulator_id,
            program,
            result
        )

        self._check_actions(
            manipulator_id,
            steps,
            result
        )

        self._check_first_step(
            manipulator_id,
            steps,
            result
        )

        self._check_pickup_drop_balance(
            manipulator_id,
            steps,
            result
        )

        self._check_repeated_actions(
            manipulator_id,
            steps,
            result
        )

    def _check_step_limit(
        self,
        manipulator_id,
        program,
        result
    ):
        max_steps = (
            program.max_logical_steps()
        )

        actual_steps = len(
            program.steps
        )

        if (
            actual_steps
            >
            max_steps
        ):
            result.add_error(
                manipulator_id,
                "STEP_LIMIT",
                (
                    f"Liczba kroków PLC={actual_steps}, "
                    f"limit={max_steps}."
                )
            )
        else:
            result.add_info(
                manipulator_id,
                "STEP_USAGE",
                (
                    f"Użyto "
                    f"{actual_steps}/{max_steps} kroków PLC."
                )
            )

    def _check_actions(
        self,
        manipulator_id,
        steps,
        result
    ):
        for step in steps:

            if step.action not in [
                self.ACTION_PICKUP,
                self.ACTION_DROP
            ]:
                result.add_error(
                    manipulator_id,
                    "INVALID_ACTION",
                    (
                        f"Krok {step.step_no}: "
                        f"nieprawidłowa akcja "
                        f"{step.action}."
                    )
                )

    def _check_first_step(
        self,
        manipulator_id,
        steps,
        result
    ):
        first_step = (
            steps[0]
        )

        if (
            first_step.action
            !=
            self.ACTION_PICKUP
        ):
            result.add_warning(
                manipulator_id,
                "FIRST_STEP_DROP",
                (
                    "Program zaczyna się "
                    "od OPUSC."
                )
            )

    def _check_pickup_drop_balance(
        self,
        manipulator_id,
        steps,
        result
    ):
        pickup_count = sum(
            1
            for step
            in steps
            if (
                step.action
                ==
                self.ACTION_PICKUP
            )
        )

        drop_count = sum(
            1
            for step
            in steps
            if (
                step.action
                ==
                self.ACTION_DROP
            )
        )

        if (
            pickup_count
            !=
            drop_count
        ):
            result.add_error(
                manipulator_id,
                "UNBALANCED_GRIPPER",
                (
                    f"PICKUP={pickup_count}, "
                    f"DROP={drop_count}"
                )
            )
        else:
            result.add_info(
                manipulator_id,
                "BALANCED_GRIPPER",
                (
                    f"PICKUP={pickup_count}, "
                    f"DROP={drop_count}"
                )
            )

    def _check_repeated_actions(
        self,
        manipulator_id,
        steps,
        result
    ):
        for index in range(
            len(
                steps
            )
            - 1
        ):

            current_step = (
                steps[index]
            )

            next_step = (
                steps[index + 1]
            )

            if (
                current_step.action
                ==
                next_step.action
            ):
                result.add_info(
                    manipulator_id,
                    "REPEATED_ACTION",
                    (
                        f"Krok "
                        f"{current_step.step_no}"
                        f" -> "
                        f"{next_step.step_no}: "
                        f"powtórzona akcja "
                        f"{current_step.action}."
                    )
                )