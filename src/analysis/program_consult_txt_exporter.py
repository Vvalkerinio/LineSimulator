class ProgramConsultTxtExporter:

    def __init__(
        self,
        consults
    ):
        self.consults = (
            consults
        )

    def export_text(
        self
    ):
        lines = []

        lines.append(
            "// CONSULTS"
        )

        lines.append(
            "// PLC liczy każdy WORD jako osobny index."
        )

        lines.append(
            "// Format roboczy:"
        )

        lines.append(
            "// Mx INDEX a WAIT UNTIL My INDEX b FINISHED"
        )

        lines.append(
            ""
        )

        for consult in self.consults:
            lines.append(
                consult.to_text()
            )

            lines.append(
                (
                    f"// {consult.description} "
                    f"source_time="
                    f"{consult.source_cycle_time_start:.1f}"
                    f".."
                    f"{consult.source_cycle_time_end:.1f} "
                    f"target_time="
                    f"{consult.target_cycle_time_start:.1f}"
                    f".."
                    f"{consult.target_cycle_time_end:.1f}"
                )
            )

            lines.append(
                ""
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