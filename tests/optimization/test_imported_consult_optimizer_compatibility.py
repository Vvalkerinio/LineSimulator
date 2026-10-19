from types import SimpleNamespace

from src.analysis.program_consult_txt_importer import ProgramConsultTxtImporter
from src.analysis.program_cycle_kpi import ProgramCycleKPI
from src.model.manipulator_program import ManipulatorProgram
from src.model.manipulator_program_step import ManipulatorProgramStep
from src.model.station import Station
from src.optimization import OptimizationStudyFactory
from src.optimization.program_candidate_evaluator import ProgramCandidateEvaluator


def imported_consult():
    text = "M1 INDEX 1 WAIT UNTIL M2 INDEX 4 FINISHED"
    return ProgramConsultTxtImporter().import_text(text)[0]


def configuration():
    stations = [
        Station(i, f"S{i}", True, 0, 100,
                is_process_bath=(i % 2 == 0))
        for i in range(1, 9)
    ]
    manipulators = [
        SimpleNamespace(id=1, position=1, work_zone_start=1,
                        work_zone_end=2, lift_time=1, drop_time=1,
                        travel_time_per_position=1),
        SimpleNamespace(id=2, position=3, work_zone_start=3,
                        work_zone_end=4, lift_time=1, drop_time=1,
                        travel_time_per_position=1),
        SimpleNamespace(id=3, position=5, work_zone_start=5,
                        work_zone_end=6, lift_time=1, drop_time=1,
                        travel_time_per_position=1),
        SimpleNamespace(id=4, position=7, work_zone_start=7,
                        work_zone_end=8, lift_time=1, drop_time=1,
                        travel_time_per_position=1)
    ]
    return SimpleNamespace(
        stations=stations, manipulators=manipulators,
        minimum_manipulator_spacing=2
    )


def programs():
    result = {}
    for mid, station in ((1, 1), (2, 3), (3, 5), (4, 7)):
        program = ManipulatorProgram(mid, mid * 100)
        program.steps = [ManipulatorProgramStep(
            mid, 1, 0, 1, station, station, 2, 0, "DROP"
        )]
        result[mid] = program
    return result


def test_imported_consult_has_reason_and_fingerprints():
    consult = imported_consult()
    assert consult.reason == "IMPORTED_TXT"
    factory = OptimizationStudyFactory(
        configuration(), programs, lambda: [consult]
    )
    assert len(factory.fingerprint(programs(), [consult])) == 64


def test_cycle_metrics_use_actual_program_cycle_kpi_keys():
    result = SimpleNamespace(program_cycle_kpi={
        "cycle_duration": 452.7,
        "throughput": 7.95,
        "hangers_per_cycle": 1.0
    })
    assert ProgramCandidateEvaluator._cycle_metrics(result) == (
        452.7, 7.95, 1.0
    )


def test_current_start_positions_are_generated_before_grid_corner():
    factory = OptimizationStudyFactory(
        configuration(), programs, lambda: []
    )
    first = next(factory.candidate_factory())
    assert first.start_positions == (1, 3, 5, 7)
    assert first.parking_positions == (1, 3, 5, 7)
