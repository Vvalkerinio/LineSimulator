from math import isclose
from types import SimpleNamespace
from src.analysis.theoretical_capacity_analyzer import TheoreticalCapacityAnalyzer
from src.analysis.theoretical_capacity_report import TheoreticalCapacityTextReport

def station(i, minimum, process=True, drip=0.0):
    return SimpleNamespace(id=i, enabled=True, is_process_bath=process,
        shared_bath_group=None, min_process_time=minimum, max_process_time=minimum+10,
        possible_min_process_time=minimum/2 if process else 0.0,
        possible_max_process_time=minimum+20, drip_time=drip)
def manip(i, start, end, speed, lift=2, drop=3):
    return SimpleNamespace(id=i, work_zone_start=start, work_zone_end=end,
        travel_time_per_position=speed, lift_time=lift, drop_time=drop)
def test_ideal_process_model_keeps_physics_but_ignores_conflicts():
    config=SimpleNamespace(stations=[station(1,0,False),station(2,100,True,4),station(4,0,False)],
        manipulators=[manip(1,1,4,5)], minimum_manipulator_spacing=2)
    report=TheoreticalCapacityAnalyzer().analyze(config,route=[1,2,4])
    assert isclose(report.ideal_process_nominal_throughput, 3600.0 / 119.0)
    # residence 100; handling: 1->2 = 10, 2->4 = 19 (2 lift+4 drip+10 travel+3 drop)
    assert isclose(report.ideal_path_nominal_seconds,129.0)
    assert isclose(report.ideal_path_details['nominal_handling_seconds'],29.0)
    text=TheoreticalCapacityTextReport().render(report)
    assert 'IDEAL PROCESS / PERFECT MANIPULATORS' in text
    assert 'Nominal process ceiling' in text
