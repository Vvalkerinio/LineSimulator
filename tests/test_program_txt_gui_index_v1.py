from src.analysis.manipulator_program_txt_importer import ManipulatorProgramTxtImporter


def test_import_uses_exact_gui_index_address():
    importer = ManipulatorProgramTxtImporter(
        index_addresses_by_manipulator={1: 410},
        station_offsets_by_manipulator={1: 0},
        station_id_shift=1,
        max_program_words=9
    )
    programs = importer.import_text(
        "AT %MW411 : WORD := (9);\n"
        "AT %MW412 : WORD := (1);\n"
        "AT %MW413 : WORD := (100);\n"
        "AT %MW501 : WORD := (99);\n"
    )

    program = programs[1]
    assert program.index_address == 410
    assert len(program.steps) == 1
    assert program.steps[0].plc_station_value == 9
    assert program.steps[0].wait_time_01s == 100
