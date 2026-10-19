from types import SimpleNamespace

from src.model.manipulator_program import ManipulatorProgram
from src.model.manipulator_program_step import ManipulatorProgramStep
from src.model.program_consult import ProgramConsult
from src.model.station import Station
from src.optimization import (
    OptimizationCandidate,
    ProgramCandidateTransformer
)


def step(mid, no, station, status="OK", segment="loaded_move"):
    return ManipulatorProgramStep(
        manipulator_id=mid, step_no=no,
        cycle_time_start=float(no), cycle_time_end=float(no),
        station_id=station, plc_station_value=station,
        action=2, wait_time_01s=0, command_name="DROP",
        station_name=f"S{station}", source_station=station,
        target_station=station, segment_type=segment, status=status
    )


def program(mid, stations):
    return ManipulatorProgram(
        manipulator_id=mid, index_address=mid * 100,
        max_program_words=99,
        steps=[step(mid, index + 1, station)
               for index, station in enumerate(stations)]
    )


def configuration():
    stations = [Station(i, f"S{i}", True, 0, 999,
                        is_process_bath=(i not in (1, 3, 5, 7)))
                for i in range(1, 13)]
    manipulators = [
        SimpleNamespace(id=1, work_zone_start=1, work_zone_end=4),
        SimpleNamespace(id=2, work_zone_start=3, work_zone_end=6),
        SimpleNamespace(id=3, work_zone_start=5, work_zone_end=8),
        SimpleNamespace(id=4, work_zone_start=7, work_zone_end=12)
    ]
    return SimpleNamespace(
        stations=stations, manipulators=manipulators,
        minimum_manipulator_spacing=2
    )


def consult():
    return ProgramConsult(
        source_manipulator_id=2,
        source_logical_step_no=2,
        source_plc_index=4,
        source_word_address=204,
        target_manipulator_id=3,
        target_logical_step_no=2,
        target_plc_index=4,
        target_word_address=304,
        source_cycle_time_start=0,
        source_cycle_time_end=0,
        target_cycle_time_start=0,
        target_cycle_time_end=0,
        reason="test"
    )


def test_transformer_inserts_preposition_before_protected_operation():
    programs = {
        1: program(1, [1, 2]), 2: program(2, [3, 6]),
        3: program(3, [5, 8]), 4: program(4, [7, 10])
    }
    candidate = OptimizationCandidate((1, 3, 7, 9), (1, 5, 7, 9))
    outcome = ProgramCandidateTransformer(configuration()).transform(
        programs, [consult()], candidate
    )
    assert outcome.valid
    statuses = [item.status for item in outcome.programs[2].steps]
    assert "OPTIMIZER_CONSULT_PREPOSITION" in statuses
    protected_index = outcome.consults[0].source_plc_index
    preposition_step = next(i for i, item in enumerate(
        outcome.programs[2].steps
    ) if item.status == "OPTIMIZER_CONSULT_PREPOSITION")
    assert protected_index == (preposition_step + 1) * 3 + 1


def test_transformer_adds_measured_cycle_returns():
    programs = {mid: program(mid, [mid * 2 - 1, mid * 2])
                for mid in (1, 2, 3, 4)}
    candidate = OptimizationCandidate((1, 3, 5, 7), (1, 3, 5, 7))
    outcome = ProgramCandidateTransformer(configuration()).transform(
        programs, [], candidate
    )
    assert outcome.valid
    for mid, start in enumerate(candidate.start_positions, start=1):
        last = outcome.programs[mid].steps[-1]
        assert last.status == "OPTIMIZER_CYCLE_RETURN"
        assert last.station_id == start


def test_transformer_does_not_mutate_source_program_or_consult():
    programs = {
        1: program(1, [1, 2]), 2: program(2, [3, 6]),
        3: program(3, [5, 8]), 4: program(4, [7, 10])
    }
    original = consult()
    outcome = ProgramCandidateTransformer(configuration()).transform(
        programs, [original],
        OptimizationCandidate((1, 3, 5, 7), (1, 3, 5, 7))
    )
    assert outcome.valid
    assert original.source_plc_index == 4
    assert len(programs[2].steps) == 2


def test_process_bath_parking_is_rejected_if_non_process_is_legal():
    programs = {mid: program(mid, [mid * 2 - 1]) for mid in (1, 2, 3, 4)}
    candidate = OptimizationCandidate((1, 3, 5, 7), (2, 4, 6, 8))
    outcome = ProgramCandidateTransformer(configuration()).transform(
        programs, [], candidate
    )
    assert not outcome.valid
    assert any("PROCESS_BATH_PARKING_NOT_FORCED" in item
               for item in outcome.errors)


def test_transformer_rejects_program_word_overflow():
    programs = {mid: program(mid, [mid * 2 - 1]) for mid in (1, 2, 3, 4)}
    for item in programs.values():
        item.max_program_words = 3
    outcome = ProgramCandidateTransformer(configuration()).transform(
        programs, [], OptimizationCandidate((1, 3, 5, 7), (1, 3, 5, 7))
    )
    assert not outcome.valid
    assert any("PROGRAM_WORD_LIMIT" in item for item in outcome.errors)


def test_transformer_rejects_blocked_cycle_return_path():
    programs = {mid: program(mid, [mid * 2 - 1, mid * 2])
                for mid in (1, 2, 3, 4)}
    transformer = ProgramCandidateTransformer(
        configuration(),
        path_validator=lambda mid, source, target: not (
            mid == 1 and source == 2 and target == 1
        )
    )
    outcome = transformer.transform(
        programs, [], OptimizationCandidate((1, 3, 5, 7), (1, 3, 5, 7))
    )
    assert not outcome.valid
    assert any("CYCLE_RETURN_PATH_BLOCKED" in item
               for item in outcome.errors)


def test_consult_remap_audit_preserves_source_and_target_commands():
    programs = {
        1: program(1, [1, 2]), 2: program(2, [3, 6]),
        3: program(3, [5, 8]), 4: program(4, [7, 10])
    }
    original = consult()
    outcome = ProgramCandidateTransformer(configuration()).transform(
        programs,
        [original],
        OptimizationCandidate((1, 3, 7, 9), (1, 5, 7, 9))
    )
    assert outcome.valid
    assert len(outcome.consult_remap_audit) == 1
    audit = outcome.consult_remap_audit[0]
    assert audit["source_preserved"] is True
    assert audit["target_preserved"] is True
    assert audit["source"][1] > audit["source"][0]
    assert audit["target"][1] > audit["target"][0]


def test_consult_remap_audit_rejects_invalid_imported_index():
    programs = {
        1: program(1, [1, 2]), 2: program(2, [3, 6]),
        3: program(3, [5, 8]), 4: program(4, [7, 10])
    }
    invalid = consult()
    invalid.source_plc_index = 100
    outcome = ProgramCandidateTransformer(configuration()).transform(
        programs,
        [invalid],
        OptimizationCandidate((1, 3, 7, 9), (1, 5, 7, 9))
    )
    assert not outcome.valid
    assert any("CONSULT_SOURCE" in error for error in outcome.errors)
