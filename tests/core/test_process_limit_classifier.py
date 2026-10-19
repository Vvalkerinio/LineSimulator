import pytest
from src.model.station import Station
from src.core.process_limit_classifier import assess_process_time, validate_station_process_limits

@pytest.fixture
def station():
    return Station(2, "Bath", True, 230, 300,
                   possible_min_process_time=210,
                   possible_max_process_time=330)

@pytest.mark.parametrize("actual,status,deviation,hard", [
    (209, "HARD_MIN_VIOLATION", 21, True),
    (210, "TRADEOFF_MIN", 20, False),
    (229, "TRADEOFF_MIN", 1, False),
    (230, "OK", 0, False),
    (300, "OK", 0, False),
    (301, "TRADEOFF_MAX", 1, False),
    (330, "TRADEOFF_MAX", 30, False),
    (331, "HARD_MAX_VIOLATION", 31, True),
])
def test_classification(station, actual, status, deviation, hard):
    result = assess_process_time(station, actual)
    assert result.status == status
    assert result.nominal_deviation == deviation
    assert result.hard_violation is hard

def test_invalid_limit_order_is_rejected():
    station = Station(2, "Bad", True, 230, 300,
                      possible_min_process_time=240,
                      possible_max_process_time=330)
    with pytest.raises(ValueError, match="Possible Min"):
        validate_station_process_limits(station)
