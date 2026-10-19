import ast
from pathlib import Path


def test_process_tab_has_stable_ten_column_constants():
    path = Path("src/gui/process_tab.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ProcessTab")
    values = {}
    for node in cls.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Constant):
                values[node.targets[0].id] = node.value.value
    assert values["COLUMN_POSSIBLE_MIN"] == 4
    assert values["COLUMN_MIN_TIME"] == 5
    assert values["COLUMN_MAX_TIME"] == 6
    assert values["COLUMN_POSSIBLE_MAX"] == 7
    assert values["COLUMN_DRIP_TIME"] == 8
    assert values["COLUMN_SHARED_BATH"] == 9
