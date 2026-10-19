from dataclasses import dataclass


@dataclass
class ProcessComplianceRecord:
    hanger_id: int

    station_id: int

    entry_time: float
    exit_time: float

    actual_time: float

    min_time: float
    max_time: float

    min_ok: bool
    max_ok: bool

    violation_type: str

    possible_min_time: float | None = None
    possible_max_time: float | None = None
    possible_min_ok: bool = True
    possible_max_ok: bool = True
    compliance_status: str = "OK"
    nominal_deviation: float = 0.0