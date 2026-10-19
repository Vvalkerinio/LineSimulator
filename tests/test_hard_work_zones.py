import ast
from pathlib import Path

from src.core.assignment_selector import AssignmentSelector
from src.io.configuration_serializer import (
    _manipulator_from_dict,
    _manipulator_to_dict,
)
from src.model.manipulator import Manipulator


def manipulator():
    return Manipulator(
        id=2,
        position=8,
        lift_time=3.0,
        drop_time=3.0,
        travel_time_per_position=1.0,
        work_zone_start=5,
        work_zone_end=14,
    )


def selector_without_services():
    return AssignmentSelector.__new__(AssignmentSelector)


def test_transport_inside_zone_is_allowed():
    selector = selector_without_services()
    assert selector._is_allowed_by_work_zone(manipulator(), 5, 14)


def test_source_outside_zone_is_rejected():
    selector = selector_without_services()
    assert not selector._is_allowed_by_work_zone(manipulator(), 4, 14)


def test_target_outside_zone_is_rejected():
    selector = selector_without_services()
    assert not selector._is_allowed_by_work_zone(manipulator(), 5, 15)


def test_both_positions_outside_zone_are_rejected():
    selector = selector_without_services()
    assert not selector._is_allowed_by_work_zone(manipulator(), 1, 22)


def test_legacy_json_keys_are_ignored():
    loaded = _manipulator_from_dict({
        "id": 2,
        "position": 8,
        "lift_time": 3.0,
        "drop_time": 3.0,
        "travel_time_per_position": 1.0,
        "work_zone_start": 5,
        "work_zone_end": 14,
        "strict_work_zone": False,
        "zone_penalty": 9999.0,
    })
    assert loaded.work_zone_start == 5
    assert loaded.work_zone_end == 14
    assert not hasattr(loaded, "strict_work_zone")
    assert not hasattr(loaded, "zone_penalty")


def test_new_json_does_not_write_obsolete_zone_keys():
    data = _manipulator_to_dict(manipulator())
    assert data["work_zone_start"] == 5
    assert data["work_zone_end"] == 14
    assert "strict_work_zone" not in data
    assert "zone_penalty" not in data


def test_manipulator_gui_has_exactly_eight_headers():
    tree = ast.parse(Path("src/gui/manipulator_tab.py").read_text(encoding="utf-8"))
    class_node = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ManipulatorsTab"
    )
    headers_node = next(
        node for node in class_node.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "HEADERS"
    )
    headers = [item.value for item in headers_node.value.elts]
    assert headers == [
        "ID",
        "Pozycja startowa [ST]",
        "Podnoszenie [s]",
        "Opuszczanie [s]",
        "Czas / pozycję [s]",
        "Ulubiony parking [ST]",
        "Strefa od [ST]",
        "Strefa do [ST]",
    ]
