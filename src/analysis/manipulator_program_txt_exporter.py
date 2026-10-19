class ManipulatorProgramTxtExporter:

    def __init__(
        self,
        programs
    ):
        self.programs = programs

    def _format_line(
        self,
        address,
        value
    ):
        return (
            f"AT %MW{address} : WORD := ({value});"
        )

    def export_text(
        self
    ):
        lines = []

        for manipulator_id in sorted(
            self.programs.keys()
        ):
            program = self.programs[
                manipulator_id
            ]

            lines.append(
                self._format_line(
                    program.index_address,
                    0
                )
            )

            for index, value in enumerate(
                program.words(),
                start=1
            ):
                lines.append(
                    self._format_line(
                        program.index_address + index,
                        value
                    )
                )

        return "\n".join(
            lines
        )

    def save(
        self,
        path
    ):
        text = (
            self.export_text()
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(
                text
            )

        return path