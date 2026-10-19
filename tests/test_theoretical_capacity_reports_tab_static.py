import ast
from pathlib import Path


def source():
    return Path("src/gui/reports_tab.py").read_text(encoding="utf-8")


def test_reports_tab_recognizes_theoretical_capacity_heading():
    text = source()
    assert '"THEORETICAL CAPACITY REPORT"' in text
    assert '"Theoretical Capacity"' in text


def test_theoretical_capacity_is_before_lead_time_in_preferred_order():
    tree = ast.parse(source())
    method = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "show_report_text"
    )
    assignment = next(
        node for node in method.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "preferred_order"
    )
    values = [item.value for item in assignment.value.elts if isinstance(item, ast.Constant)]
    assert values[0] == "Theoretical Capacity"
    assert values[1] == "Lead Time"


def test_theoretical_capacity_section_keeps_full_report_until_next_heading():
    text = source()
    theoretical_position = text.index('"THEORETICAL CAPACITY REPORT"')
    lead_time_position = text.index('"LOAD TO UNLOAD LEAD TIME REPORT"')
    assert theoretical_position < lead_time_position
    block = text[theoretical_position:lead_time_position]
    assert 'current_name = (' in block
    assert '"Theoretical Capacity"' in block
    assert 'current_buffer = [' in block
    assert 'continue' in block
