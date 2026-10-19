from types import SimpleNamespace
import pytest
from src.core.simulation_preflight import (
    SimulationPreflightError,
    SimulationPreflightValidator,
)


def manip(i, pos, start, end, parking=None):
    return SimpleNamespace(
        id=i, position=pos, work_zone_start=start, work_zone_end=end,
        preferred_parking_position=pos if parking is None else parking,
    )


def station(i, pmin=10, nmin=20, nmax=30, pmax=40):
    return SimpleNamespace(
        id=i, is_process_bath=True,
        possible_min_process_time=pmin, min_process_time=nmin,
        max_process_time=nmax, possible_max_process_time=pmax,
    )


def config(manips, stations=()):
    return SimpleNamespace(
        manipulators=manips, stations=stations,
        minimum_manipulator_spacing=2.0,
    )


def test_safe_start_passes():
    assert SimulationPreflightValidator().validate(config([
        manip(1, 5, 1, 9), manip(2, 11, 5, 14),
        manip(3, 16, 12, 19), manip(4, 22, 18, 22),
    ]))


def test_collision_at_time_zero_fails_before_run():
    with pytest.raises(SimulationPreflightError, match='odstęp startowy 1.0'):
        SimulationPreflightValidator().validate(config([
            manip(1, 5, 1, 9), manip(2, 14, 5, 14),
            manip(3, 15, 12, 19), manip(4, 22, 18, 22),
        ]))


def test_out_of_zone_parking_and_bad_process_limits_fail():
    with pytest.raises(SimulationPreflightError) as error:
        SimulationPreflightValidator().validate(config(
            [manip(1, 5, 1, 9, parking=10)],
            [station(1, pmin=25, nmin=20)]
        ))
    assert 'parking 10' in str(error.value)
    assert 'Possible Min <= Min <= Max <= Possible Max' in str(error.value)
