from types import SimpleNamespace

from src.optimization import (
    OptimizationConstraints, ParkingPositionSelector,
    ConsultSafeApproachPlanner, ConsultWaitAnalyzer,
    CycleClosureValidator
)


def station(position, process):
    return SimpleNamespace(id=position, is_process_bath=process)


def test_one_free_position_blocks_adjacent_stations():
    constraints = OptimizationConstraints(minimum_position_difference=2)
    assert constraints.minimum_position_difference == 2
    # M2 occupies ST15, therefore M3 cannot occupy adjacent ST16.
    assert not constraints.is_legal_position(3, 16, (10, 15, 18, 22))
    assert constraints.is_legal_position(3, 17, (10, 15, 18, 22))


def test_strict_manipulator_order_is_required():
    violations = OptimizationConstraints(2).validate_positions((3, 3, 10, 20))
    assert any(item.code == "MANIPULATOR_ORDER" for item in violations)


def test_non_process_parking_is_preferred_over_closer_process_bath():
    constraints = OptimizationConstraints(2)
    selector = ParkingPositionSelector(constraints)
    stations = [station(pos, pos not in (10, 13)) for pos in range(1, 23)]
    decision = selector.select(
        manipulator_id=2,
        current_positions=(2, 8, 16, 22),
        target_position=14,
        stations=stations,
        zone_start=5,
        zone_end=14
    )
    assert decision.position == 13
    assert decision.is_process_bath is False
    assert decision.forced_process_bath is False


def test_consult_wait_is_reduced_by_safe_productive_approach():
    constraints = OptimizationConstraints(2)
    selector = ParkingPositionSelector(constraints)
    planner = ConsultSafeApproachPlanner(selector)
    stations = [station(pos, pos not in (11,)) for pos in range(1, 23)]
    plan = planner.plan(
        manipulator_id=1,
        current_positions=(8, 14, 18, 22),
        target_position=15,
        current_time=100.0,
        predicted_release_time=120.0,
        travel_time_per_position=2.0,
        stations=stations,
        zone_start=1,
        zone_end=13
    )
    assert plan.approach_position == 11
    assert plan.travel_time == 6.0
    assert plan.gross_consult_wait == 20.0
    assert plan.productive_approach_time == 6.0
    assert plan.net_idle_wait == 14.0
    summary = ConsultWaitAnalyzer().summarize([plan])
    assert summary["net_idle_wait"] == 14.0


def test_cycle_must_end_in_start_positions():
    violations = CycleClosureValidator().validate(
        (2, 8, 15, 22), (2, 9, 15, 22)
    )
    assert any(v.code == "CYCLE_POSITION_NOT_CLOSED" for v in violations)


def test_active_consult_cannot_cross_cycle_boundary():
    violations = CycleClosureValidator().validate(
        (2, 8, 15, 22), (2, 8, 15, 22), active_consults=[object()]
    )
    assert any(v.code == "CYCLE_ACTIVE_CONSULT" for v in violations)
