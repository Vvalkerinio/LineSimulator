from types import SimpleNamespace

from src.io.configuration_serializer import (
    _station_from_dict,
    _station_to_dict,
    create_default_configuration
)
from src.optimization import CandidateGenerator, OptimizationConstraints
from src.model.station import Station


def manipulator(mid, start, end):
    return SimpleNamespace(id=mid, work_zone_start=start, work_zone_end=end)


def test_process_bath_round_trip():
    station = Station(4, "P4", True, 10, 20, is_process_bath=False)
    restored = _station_from_dict(_station_to_dict(station))
    assert restored.is_process_bath is False


def test_legacy_process_bath_defaults_are_safe():
    common = {"name": "X", "enabled": True,
              "min_process_time": 0, "max_process_time": 10}
    assert _station_from_dict({"id": 1, **common}).is_process_bath is False
    assert _station_from_dict({"id": 22, **common}).is_process_bath is False
    assert _station_from_dict({"id": 10, **common}).is_process_bath is True


def test_default_load_and_unload_are_non_process():
    config = create_default_configuration()
    by_id = {station.id: station for station in config.stations}
    assert by_id[1].is_process_bath is False
    assert by_id[22].is_process_bath is False
    assert by_id[10].is_process_bath is True


def test_candidate_generator_respects_order_spacing_and_zones():
    manipulators = [
        manipulator(1, 1, 2), manipulator(2, 3, 4),
        manipulator(3, 5, 6), manipulator(4, 7, 8)
    ]
    constraints = OptimizationConstraints(minimum_position_difference=2)
    candidates = list(CandidateGenerator(constraints).generate(
        manipulators,
        parking_positions_by_manipulator={1: [1], 2: [3], 3: [5], 4: [7]}
    ))
    assert candidates
    assert all(not constraints.validate_positions(
        item.start_positions, manipulators
    ) for item in candidates)
    assert all(item.parking_positions == (1, 3, 5, 7) for item in candidates)
