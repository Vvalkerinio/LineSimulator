from types import SimpleNamespace
from math import isclose

from src.analysis.theoretical_capacity_analyzer import TheoreticalCapacityAnalyzer
from src.analysis.theoretical_capacity_report import TheoreticalCapacityTextReport


def station(i, minimum, possible=None, group=None, process=True):
    return SimpleNamespace(
        id=i,
        name=f"S{i}",
        enabled=True,
        is_process_bath=process,
        min_process_time=minimum,
        possible_min_process_time=minimum if possible is None else possible,
        shared_bath_group=group,
    )


def manipulator(i, start, end, speed=1, lift=2, drop=2):
    return SimpleNamespace(
        id=i,
        work_zone_start=start,
        work_zone_end=end,
        travel_time_per_position=speed,
        lift_time=lift,
        drop_time=drop,
    )


def test_parallel_baths_sum_capacity_and_identify_bottleneck():
    config = SimpleNamespace(
        stations=[
            station(1, 0, process=False),
            station(2, 300, 240, "ODT"),
            station(3, 300, 240, "ODT"),
            station(4, 120),
            station(5, 0, process=False),
        ],
        manipulators=[manipulator(1, 1, 5)],
        route=[1, 2, 4, 5],
    )
    report = TheoreticalCapacityAnalyzer().analyze(config)
    nominal_odt = next(
        b for b in report.nominal_bounds if b.limiting_resource == "shared_bath:ODT"
    )
    possible_odt = next(
        b for b in report.possible_bounds if b.limiting_resource == "shared_bath:ODT"
    )
    assert isclose(nominal_odt.throughput_per_hour, 24.0)
    assert isclose(possible_odt.throughput_per_hour, 30.0)
    assert report.nominal_limiting_resource == "shared_bath:ODT"


def test_gap_is_reported_against_best_simulation():
    config = SimpleNamespace(
        stations=[station(1, 0, process=False), station(2, 300), station(3, 0, process=False)],
        manipulators=[manipulator(1, 1, 3)],
        route=[1, 2, 3],
    )
    report = TheoreticalCapacityAnalyzer().analyze(
        config, best_simulated_throughput=10.0
    )
    assert isclose(report.nominal_upper_bound, 12.0)
    assert isclose(report.nominal_gap, 2.0)
    assert isclose(report.nominal_relative_gap_percent, 100.0 / 6.0)
    text = TheoreticalCapacityTextReport().render(report)
    assert "Nominal certified upper bound : 12.00 szt/h" in text
    assert "Precise EventDriven           : 10.00 szt/h" in text


def test_unreachable_transition_returns_zero_transport_bound():
    config = SimpleNamespace(
        stations=[station(1, 0, process=False), station(10, 20), station(22, 0, process=False)],
        manipulators=[manipulator(1, 1, 8)],
        route=[1, 10, 22],
    )
    report = TheoreticalCapacityAnalyzer().analyze(config)
    assert report.nominal_upper_bound == 0.0
    assert report.nominal_limiting_resource == "unreachable_transition:1->10"


def test_mandatory_manipulator_bound_is_certifying():
    config = SimpleNamespace(
        stations=[station(1, 0, process=False), station(2, 30), station(3, 0, process=False)],
        manipulators=[
            manipulator(1, 1, 1),
            manipulator(2, 1, 3, speed=2, lift=3, drop=3),
        ],
        minimum_manipulator_spacing=2.0,
    )
    report = TheoreticalCapacityAnalyzer().analyze(config, route=[1, 2, 3])
    bound = next(b for b in report.nominal_bounds if b.limiting_resource == "manipulator:M2")
    assert bound.certifying is True
    assert bound.category == "manipulator"
    assert isclose(bound.details["mandatory_work_seconds_per_part"], 16.0)
    assert isclose(bound.throughput_per_hour, 225.0)


def test_interface_diagnostic_does_not_lower_certified_bound():
    config = SimpleNamespace(
        stations=[station(1, 0, process=False), station(5, 100), station(7, 0, process=False)],
        manipulators=[
            manipulator(1, 1, 5, speed=5),
            manipulator(2, 3, 8, speed=5),
        ],
        minimum_manipulator_spacing=2.0,
    )
    report = TheoreticalCapacityAnalyzer().analyze(config, route=[1, 5, 7])
    diagnostic = next(b for b in report.nominal_bounds if b.limiting_resource == "interface:M1/M2")
    assert diagnostic.certifying is False
    assert diagnostic in report.nominal_diagnostics
    assert report.nominal_upper_bound != diagnostic.throughput_per_hour


def test_route_collapses_each_shared_bath_group_once():
    config = SimpleNamespace(
        stations=[
            station(1, 0, process=False),
            station(2, 300, group="ODT"),
            station(3, 300, group="ODT"),
            station(4, 100),
            station(5, 0, process=False),
        ],
        manipulators=[manipulator(1, 1, 5)],
        minimum_manipulator_spacing=2.0,
    )
    report = TheoreticalCapacityAnalyzer().analyze(config)
    pooled = next(b for b in report.nominal_bounds if b.limiting_resource == "manipulator_pool")
    assert pooled.details["route"] == [1, 2, 4, 5]
