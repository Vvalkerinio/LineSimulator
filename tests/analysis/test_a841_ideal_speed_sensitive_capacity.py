from math import isclose
from types import SimpleNamespace
from src.analysis.theoretical_capacity_analyzer import TheoreticalCapacityAnalyzer


def station(i, minimum, process=True, group=None, drip=0.0):
    return SimpleNamespace(
        id=i, enabled=True, is_process_bath=process,
        shared_bath_group=group, min_process_time=minimum,
        max_process_time=minimum + 100,
        possible_min_process_time=minimum,
        possible_max_process_time=minimum + 150,
        drip_time=drip,
    )


def manipulator(speed):
    return SimpleNamespace(
        id=1, work_zone_start=1, work_zone_end=4,
        lift_time=6.5, drop_time=6.5,
        travel_time_per_position=speed,
    )


def config(speed):
    return SimpleNamespace(
        stations=[station(1, 0, False), station(2, 220, True, drip=10), station(4, 0, False)],
        manipulators=[manipulator(speed)],
        minimum_manipulator_spacing=2.0,
        pieces_per_transport=7,
    )


def test_ideal_process_ceiling_decreases_when_loaded_travel_slows():
    fast = TheoreticalCapacityAnalyzer().analyze(config(4.5), route=[1, 2, 4])
    slow = TheoreticalCapacityAnalyzer().analyze(config(6.0), route=[1, 2, 4])
    assert slow.ideal_path_nominal_seconds > fast.ideal_path_nominal_seconds
    assert slow.ideal_process_nominal_throughput < fast.ideal_process_nominal_throughput
    # Limiting stage 2: 220 residence + 6.5 lift + 10 drip + 2*speed + 6.5 drop.
    assert isclose(fast.ideal_process_nominal_throughput, 3600.0 / 252.0)
    assert isclose(slow.ideal_process_nominal_throughput, 3600.0 / 255.0)
    assert slow.ideal_path_details['nominal_limiting_resource'] == 'station:2'
