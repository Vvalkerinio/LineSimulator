"""Shared deterministic formatting for plain-text report tables."""


def format_text_table(headers, rows, alignments=None, gap=2):
    headers = [str(value) for value in headers]
    normalized = [[str(value) for value in row] for row in rows]
    if any(len(row) != len(headers) for row in normalized):
        raise ValueError("Every table row must match the header column count")
    widths = [len(header) for header in headers]
    for row in normalized:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    alignments = list(alignments or ("left",) * len(headers))
    if len(alignments) != len(headers):
        raise ValueError("Every table column must have an alignment")

    def cell(value, width, alignment):
        if alignment == "right":
            return value.rjust(width)
        if alignment == "center":
            return value.center(width)
        return value.ljust(width)

    separator = " " * max(1, int(gap))
    lines = [separator.join(
        cell(headers[index], widths[index], "center")
        for index in range(len(headers))
    )]
    lines.append(separator.join("-" * width for width in widths))
    for row in normalized:
        lines.append(separator.join(
            cell(row[index], widths[index], alignments[index])
            for index in range(len(headers))
        ))
    return "\n".join(lines)
