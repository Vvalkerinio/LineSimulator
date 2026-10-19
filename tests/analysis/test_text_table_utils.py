from src.analysis.text_table_utils import format_text_table


def test_dynamic_widths_and_numeric_alignment_are_stable():
    result = format_text_table(
        ["Name", "Count", "Value"],
        [["ODT", "2", "9.5"], ["Long station name", "120", "1000.0"]],
        ["left", "right", "right"]
    )
    lines = result.splitlines()
    assert len({len(line) for line in lines}) == 1
    assert lines[2].startswith("ODT")
    assert lines[3].startswith("Long station name")
    assert lines[2].index("2") == lines[3].index("120") + 2


def test_rejects_rows_with_different_column_count():
    try:
        format_text_table(["A", "B"], [["one"]])
    except ValueError as exc:
        assert "column count" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
