from types import SimpleNamespace

from src.model.manipulator_program import ManipulatorProgram
from src.model.manipulator_program_step import ManipulatorProgramStep
from src.model.program_consult import ProgramConsult
from src.model.station import Station
from src.optimization import OptimizationStudyFactory


def configuration():
    stations = [
        Station(i, f"S{i}", True, 0, 100,
                is_process_bath=(i not in (1, 3, 5, 7)))
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
        item = ManipulatorProgram(mid, mid * 100)
        item.steps = [ManipulatorProgramStep(
            mid, 1, 0, 0, station, station, 2, 0, "DROP"
        )]
        result[mid] = item
    return result


def test_factory_fingerprint_is_deterministic_and_program_sensitive():
    current = programs()
    factory = OptimizationStudyFactory(
        configuration(), lambda: current, lambda: []
    )
    first = factory.fingerprint(current, [])
    second = factory.fingerprint(current, [])
    assert first == second
    current[1].steps[0].wait_time_01s = 10
    assert factory.fingerprint(current, []) != first


def test_candidate_factory_uses_only_non_process_parking_when_available():
    factory = OptimizationStudyFactory(
        configuration(), programs, lambda: []
    )
    candidates = list(factory.candidate_factory())
    assert candidates
    # Each narrow zone has exactly one non-process position.
    assert all(item.parking_positions == (1, 3, 5, 7)
               for item in candidates)
