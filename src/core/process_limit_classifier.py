from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessLimitAssessment:
    status: str
    nominal_min_ok: bool
    nominal_max_ok: bool
    possible_min_ok: bool
    possible_max_ok: bool
    nominal_deviation: float

    @property
    def hard_violation(self):
        return not self.possible_min_ok or not self.possible_max_ok

    @property
    def tradeoff(self):
        return self.status in ("TRADEOFF_MIN", "TRADEOFF_MAX")


def station_process_limits(station):
    nominal_min = float(station.min_process_time)
    nominal_max = float(station.max_process_time)
    possible_min = getattr(station, "possible_min_process_time", None)
    possible_max = getattr(station, "possible_max_process_time", None)
    possible_min = nominal_min if possible_min is None else float(possible_min)
    possible_max = nominal_max if possible_max is None else float(possible_max)
    return possible_min, nominal_min, nominal_max, possible_max


def validate_station_process_limits(station):
    possible_min, nominal_min, nominal_max, possible_max = station_process_limits(station)
    if not (0.0 <= possible_min <= nominal_min <= nominal_max <= possible_max):
        raise ValueError(
            f"Station {station.id}: required 0 <= Possible Min <= Min <= Max <= Possible Max; "
            f"got {possible_min}, {nominal_min}, {nominal_max}, {possible_max}"
        )
    return possible_min, nominal_min, nominal_max, possible_max


TIME_EPSILON = 1e-6


def assess_process_time(station, actual_time):
    possible_min, nominal_min, nominal_max, possible_max = validate_station_process_limits(station)
    actual = float(actual_time)
    if actual < possible_min - TIME_EPSILON:
        status = "HARD_MIN_VIOLATION"
    elif actual < nominal_min - TIME_EPSILON:
        status = "TRADEOFF_MIN"
    elif actual <= nominal_max + TIME_EPSILON:
        status = "OK"
    elif actual <= possible_max + TIME_EPSILON:
        status = "TRADEOFF_MAX"
    else:
        status = "HARD_MAX_VIOLATION"
    deviation = max(nominal_min - actual, 0.0, actual - nominal_max)
    if deviation <= TIME_EPSILON:
        deviation = 0.0
    return ProcessLimitAssessment(
        status=status,
        nominal_min_ok=actual >= nominal_min - TIME_EPSILON,
        nominal_max_ok=actual <= nominal_max + TIME_EPSILON,
        possible_min_ok=actual >= possible_min - TIME_EPSILON,
        possible_max_ok=actual <= possible_max + TIME_EPSILON,
        nominal_deviation=float(deviation)
    )
