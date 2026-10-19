from src.analysis.manipulator_program_txt_importer import (
    ManipulatorProgramTxtImporter
)


def test_import_simple_program():
    text = """
AT %MW501 : WORD := (9);
AT %MW502 : WORD := (1);
AT %MW503 : WORD := (10);
"""

    importer = ManipulatorProgramTxtImporter(
        index_addresses_by_manipulator={
            1: 500
        },
        station_offsets_by_manipulator={
            1: 0
        },
        station_id_shift=1,
        max_program_words=100
    )

    programs = (
        importer.import_text(
            text
        )
    )

    program = (
        programs[
            1
        ]
    )

    assert len(
        program.steps
    ) == 1

    step = (
        program.steps[
            0
        ]
    )

    assert step.plc_station_value == 9
    assert step.station_id == 8
    assert step.action == 1
    assert step.wait_time_01s == 10