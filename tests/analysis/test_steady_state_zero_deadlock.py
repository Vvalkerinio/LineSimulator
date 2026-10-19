from types import SimpleNamespace
from src.analysis.steady_state_detector import SteadyStateDetector

def test_zero_throughput_with_deferred_transports_is_not_steady_state():
    result = SimpleNamespace(
        final_time=1800.0,
        hanger_exit_times={},
        deferred_transports=[object()],
        deadlocks=[]
    )
    detected = SteadyStateDetector(required_windows=2).detect(
        result, window_size=300.0, analysis_start=0.0, analysis_end=1800.0
    )
    assert detected["detected"] is False
    assert detected["reason"] == "stable_zero_deadlock"
