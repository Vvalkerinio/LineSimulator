"""PLC-aligned user-facing station numbering.

Internal coordinates remain 1..22 for geometry and compatibility. All values
shown to or entered by a user are shifted to 2..23.
"""
STATION_ID_SHIFT = 1
MIN_DISPLAY_STATION_ID = 2


def display_station_id(internal_id):
    return None if internal_id is None else int(internal_id) + STATION_ID_SHIFT


def internal_station_id(display_id):
    if display_id is None:
        return None
    display_id = int(display_id)
    if display_id < MIN_DISPLAY_STATION_ID:
        raise ValueError("Numer stanowiska musi być większy lub równy 2.")
    return display_id - STATION_ID_SHIFT


def display_station_label(internal_id):
    value = display_station_id(internal_id)
    return "-" if value is None else f"ST{value}"
