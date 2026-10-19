import re

from src.model.manipulator_program import (
    ManipulatorProgram
)

from src.model.manipulator_program_step import (
    ManipulatorProgramStep
)


class ManipulatorProgramTxtImporter:

    LINE_PATTERN = re.compile(
        r"AT\s+%MW(?P<address>\d+)\s*:\s*WORD\s*:=\s*\((?P<value>-?\d+)\)\s*;",
        re.IGNORECASE
    )

    def __init__(
        self,
        index_addresses_by_manipulator,
        station_offsets_by_manipulator=None,
        station_id_shift=1,
        max_program_words=99
    ):
        if not index_addresses_by_manipulator:
            raise ValueError(
                "Brak adresów MW Index przekazanych z GUI."
            )

        self.index_addresses_by_manipulator = {
            int(manipulator_id): int(index_address)
            for manipulator_id, index_address
            in index_addresses_by_manipulator.items()
        }

        self.station_offsets_by_manipulator = {
            int(manipulator_id): int(offset)
            for manipulator_id, offset
            in (station_offsets_by_manipulator or {}).items()
        }

        self.station_id_shift = int(
            station_id_shift
        )

        self.max_program_words = int(
            max_program_words
        )

    def configured_ranges(
        self
    ):
        return {
            manipulator_id: (
                index_address + 1,
                index_address + self.max_program_words
            )
            for manipulator_id, index_address
            in self.index_addresses_by_manipulator.items()
        }

    def _validate_index_addresses(
        self
    ):
        addresses = list(
            self.index_addresses_by_manipulator.values()
        )
        if len(addresses) != len(set(addresses)):
            raise ValueError(
                "Adresy MW Index manipulatorów muszą być unikalne."
            )
        for manipulator_id, address in (
            self.index_addresses_by_manipulator.items()
        ):
            if address < 0:
                raise ValueError(
                    f"M{manipulator_id}: MW Index nie może być ujemny."
                )

    def _parse_words(
        self,
        text
    ):
        values_by_address = {}

        for line in text.splitlines():
            match = (
                self.LINE_PATTERN.search(
                    line
                )
            )

            if match is None:
                continue

            address = int(
                match.group(
                    "address"
                )
            )

            value = int(
                match.group(
                    "value"
                )
            )

            values_by_address[
                address
            ] = value

        return values_by_address

    def _command_name(
        self,
        action
    ):
        if action == 1:
            return "PODNIES"

        if action == 2:
            return "OPUSC"

        return "NIEZNANA"

    def _program_for_manipulator(
        self,
        manipulator_id,
        values_by_address
    ):
        index_address = int(
            self.index_addresses_by_manipulator[
                manipulator_id
            ]
        )

        station_offset = int(
            self.station_offsets_by_manipulator.get(
                manipulator_id,
                0
            )
        )

        program = ManipulatorProgram(
            manipulator_id=(
                manipulator_id
            ),
            index_address=(
                index_address
            ),
            station_offset=(
                station_offset
            ),
            station_id_shift=(
                self.station_id_shift
            ),
            max_program_words=(
                self.max_program_words
            )
        )

        words = []

        for index in range(
            1,
            self.max_program_words
            +
            1
        ):
            words.append(
                values_by_address.get(
                    index_address
                    +
                    index,
                    0
                )
            )

        steps = []

        step_no = 1

        for index in range(
            0,
            len(
                words
            )
            -
            2,
            3
        ):
            station_word = (
                words[
                    index
                ]
            )

            action = (
                words[
                    index
                    +
                    1
                ]
            )

            wait_time_01s = (
                words[
                    index
                    +
                    2
                ]
            )

            if (
                station_word == 0
                and
                action == 0
                and
                wait_time_01s == 0
            ):
                continue

            simulation_station_id = (
                station_word
                +
                station_offset
                -
                self.station_id_shift
            )

            status = "IMPORTED"

            if action not in [
                1,
                2
            ]:
                status = (
                    f"INVALID_ACTION_{action}"
                )

            steps.append(
                ManipulatorProgramStep(
                    manipulator_id=(
                        manipulator_id
                    ),
                    step_no=(
                        step_no
                    ),
                    cycle_time_start=(
                        0.0
                    ),
                    cycle_time_end=(
                        0.0
                    ),
                    station_id=(
                        simulation_station_id
                    ),
                    plc_station_value=(
                        station_word
                    ),
                    action=(
                        action
                    ),
                    wait_time_01s=(
                        wait_time_01s
                    ),
                    command_name=(
                        self._command_name(
                            action
                        )
                    ),
                    station_name="",
                    source_station=None,
                    target_station=(
                        simulation_station_id
                    ),
                    source_name="",
                    target_name="",
                    hanger_id=None,
                    segment_type="imported",
                    crosses_foreign_zone=False,
                    foreign_zone_owner=None,
                    status=(
                        status
                    )
                )
            )

            step_no += 1

        program.steps = steps

        return program

    def import_text(
        self,
        text
    ):
        self._validate_index_addresses()

        print(
            "PLC TXT IMPORT MW INDEX: "
            f"{self.index_addresses_by_manipulator}"
        )
        print(
            "PLC TXT IMPORT RANGES: "
            f"{self.configured_ranges()}"
        )

        values_by_address = (
            self._parse_words(
                text
            )
        )

        programs = {}

        for manipulator_id in sorted(
            self.index_addresses_by_manipulator.keys()
        ):
            programs[
                manipulator_id
            ] = (
                self._program_for_manipulator(
                    manipulator_id,
                    values_by_address
                )
            )

        return programs

    def import_file(
        self,
        path
    ):
        with open(
            path,
            "r",
            encoding="utf-8-sig"
        ) as file:
            text = (
                file.read()
            )

        return (
            self.import_text(
                text
            )
        )