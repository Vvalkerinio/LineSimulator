from types import SimpleNamespace

from src.analysis.event_throughput_analyzer import EventThroughputAnalyzer
from src.model.event_type import EventType


def event(time):
    return SimpleNamespace(time=time, event_type=EventType.HANGER_EXIT)


def test_interval_estimator_is_continuous_not_window_quantized():
    result = SimpleNamespace(
        final_time=1800.0,
        events=[event(100.0), event(397.0), event(701.0), event(995.0)]
    )
    metrics = EventThroughputAnalyzer().analyze(result, 0.0, 1800.0)
    assert metrics["count_rate_per_hour"] == 8.0
    assert round(metrics["interval_rate_per_hour"], 3) == 12.067
    assert metrics["exit_count"] == 4


def test_analysis_uses_half_open_range():
    result = SimpleNamespace(
        final_time=1200.0,
        events=[event(0.0), event(300.0), event(600.0), event(1200.0)]
    )
    metrics = EventThroughputAnalyzer().analyze(result, 300.0, 1200.0)
    assert metrics["exit_count"] == 2
    assert metrics["interval_rate_per_hour"] == 12.0
