from types import SimpleNamespace

from src.core.assignment_selector import AssignmentSelector
from src.core.process_limit_classifier import assess_process_time
from src.io.configuration_serializer import _manipulator_from_dict, _manipulator_to_dict


def station(station_id, process=False, enabled=True):
    return SimpleNamespace(
        id=station_id,
        enabled=enabled,
        is_process_bath=process,
        min_process_time=230.0,
        max_process_time=300.0,
        possible_min_process_time=230.0,
        possible_max_process_time=350.0,
    )


def test_float_noise_at_hard_min_is_ok():
    result = assess_process_time(station(3, process=True), 229.99999999999994)
    assert result.status == "OK"
    assert result.possible_min_ok is True
    assert result.nominal_min_ok is True
    assert result.nominal_deviation == 0.0


def test_real_minimum_violation_is_not_hidden():
    result = assess_process_time(station(3, process=True), 229.99)
    assert result.status == "HARD_MIN_VIOLATION"
    assert result.possible_min_ok is False


def test_preferred_non_process_parking_wins_over_nearest():
    selector = AssignmentSelector.__new__(AssignmentSelector)
    selector.station_map = {
        5: station(5, process=False),
        6: station(6, process=False),
        8: station(8, process=True),
        11: station(11, process=False),
    }
    manipulator = SimpleNamespace(
        id=2, position=8, preferred_parking_position=11,
        work_zone_start=5, work_zone_end=14
    )
    positions = selector._non_process_return_positions(manipulator, 6, 8)
    assert positions[0] == 11


def test_invalid_favorite_falls_back_to_legal_non_process():
    selector = AssignmentSelector.__new__(AssignmentSelector)
    selector.station_map = {
        5: station(5, process=False),
        8: station(8, process=True),
        11: station(11, process=True),
    }
    manipulator = SimpleNamespace(
        id=2, position=8, preferred_parking_position=11,
        work_zone_start=5, work_zone_end=14
    )
    positions = selector._non_process_return_positions(manipulator, 6, 8)
    assert positions == [5]


def test_preferred_parking_serialization_and_legacy_default():
    legacy = {
        "id": 2, "position": 11, "lift_time": 6.5,
        "drop_time": 6.5, "travel_time_per_position": 4.3,
        "work_zone_start": 5, "work_zone_end": 14,
    }
    old = _manipulator_from_dict(legacy)
    assert old.preferred_parking_position == 11
    legacy["preferred_parking_position"] = 12
    new = _manipulator_from_dict(legacy)
    assert new.preferred_parking_position == 12
    assert _manipulator_to_dict(new)["preferred_parking_position"] == 12
