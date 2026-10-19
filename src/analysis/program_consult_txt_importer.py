import re


class ImportedProgramConsult:

    def __init__(
        self,
        source_manipulator_id,
        source_plc_index,
        target_manipulator_id,
        target_plc_index,
        description="IMPORTED TXT"
    ):
        self.source_manipulator_id = int(source_manipulator_id)
        self.source_plc_index = int(source_plc_index)
        self.source_logical_step_no = ((self.source_plc_index - 1) // 3) + 1
        self.source_word_address = 0
        self.target_manipulator_id = int(target_manipulator_id)
        self.target_plc_index = int(target_plc_index)
        self.target_logical_step_no = ((self.target_plc_index - 1) // 3) + 1
        self.target_word_address = 0
        self.source_cycle_time_start = 0.0
        self.source_cycle_time_end = 0.0
        self.target_cycle_time_start = 0.0
        self.target_cycle_time_end = 0.0
        self.description = str(description)
        # Keep the imported lightweight model compatible with ProgramConsult.
        self.reason = "IMPORTED_TXT"

    def to_text(
        self
    ):
        return (
            f"M{self.source_manipulator_id} "
            f"INDEX {self.source_plc_index} WAIT UNTIL "
            f"M{self.target_manipulator_id} "
            f"INDEX {self.target_plc_index} FINISHED"
        )


class ProgramConsultTxtImporter:

    CONSULT_PATTERN = re.compile(
        r"^\s*M(?P<source_m>\d+)\s+INDEX\s+(?P<source_index>\d+)"
        r"\s+WAIT\s+UNTIL\s+M(?P<target_m>\d+)"
        r"\s+INDEX\s+(?P<target_index>\d+)\s+FINISHED\s*$",
        re.IGNORECASE
    )

    def import_text(
        self,
        text
    ):
        consults = []
        pending_description = None

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("//"):
                comment = line[2:].strip()
                if comment and not comment.upper().startswith((
                    "CONSULTS",
                    "PLC ",
                    "FORMAT "
                )):
                    pending_description = comment
                continue

            match = self.CONSULT_PATTERN.match(
                line
            )
            if match is None:
                continue

            consults.append(
                ImportedProgramConsult(
                    source_manipulator_id=match.group("source_m"),
                    source_plc_index=match.group("source_index"),
                    target_manipulator_id=match.group("target_m"),
                    target_plc_index=match.group("target_index"),
                    description=(
                        pending_description
                        or
                        "IMPORTED TXT"
                    )
                )
            )
            pending_description = None

        return consults

    def import_file(
        self,
        path
    ):
        with open(
            path,
            "r",
            encoding="utf-8-sig"
        ) as file:
            return self.import_text(
                file.read()
            )
