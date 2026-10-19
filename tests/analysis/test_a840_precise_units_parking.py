from types import SimpleNamespace
from src.analysis.theoretical_capacity_analyzer import TheoreticalCapacityReport
from src.analysis.theoretical_capacity_report import TheoreticalCapacityTextReport
from src.core.assignment_selector import AssignmentSelector


def test_theoretical_output_scales_transports_to_parts():
    report = TheoreticalCapacityReport(
        nominal_bounds=(), possible_bounds=(), nominal_upper_bound=16.36,
        possible_upper_bound=18.0, nominal_limiting_resource='station:19',
        possible_limiting_resource='station:19', best_simulated_throughput=9.89,
        ideal_process_nominal_throughput=16.36,
        ideal_process_possible_throughput=18.0,
        pieces_per_transport=7,
    )
    text = TheoreticalCapacityTextReport().render(report)
    assert 'Precise EventDriven           : 69.23 szt/h' in text
    assert 'precise transports          : 9.89 transportów/h' in text
    assert 'Nominal certified upper bound : 114.52 szt/h' in text
    assert 'Best EventDriven' not in text


def test_process_bath_returns_offer_safe_alternatives_before_bath_fallback():
    selector = AssignmentSelector.__new__(AssignmentSelector)
    selector.station_map = {
        3: SimpleNamespace(id=3, enabled=True, is_process_bath=True),
        5: SimpleNamespace(id=5, enabled=True, is_process_bath=False),
        6: SimpleNamespace(id=6, enabled=True, is_process_bath=False),
    }
    manipulator = SimpleNamespace(
        position=1, preferred_parking_position=5,
        work_zone_start=1, work_zone_end=9
    )
    assert selector._return_position_candidates(manipulator, 1, 3) == [3]
