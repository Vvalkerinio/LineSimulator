from types import SimpleNamespace

from src.analysis.kpi_engine import KPIEngine
from src.model.event_type import EventType


def event(time):
    return SimpleNamespace(time=time, event_type=EventType.HANGER_EXIT)


def test_kpi_engine_uses_precise_event_throughput_and_publishes_diagnostics():
    result = SimpleNamespace(
        final_time=1800.0, processed_events=4, scheduled_transports=0,
        completed_transports=0, program_cycle_kpi=None,
        events=[event(100.0), event(397.0), event(701.0), event(995.0)],
        steady_state={"analysis_start": 0.0, "analysis_end": 1800.0,
                      "throughput": 12.0}
    )
    kpi = KPIEngine().calculate(result)
    assert round(kpi.transports_per_hour, 3) == 12.067
    assert round(result.steady_state["precise_throughput"], 3) == 12.067
    assert result.steady_state["windowed_throughput"] == 12.0
    assert result.steady_state["throughput_exit_count"] == 4


def test_kpi_engine_preserves_program_driven_cycle_throughput():
    result = SimpleNamespace(
        final_time=100.0, processed_events=1, scheduled_transports=1,
        completed_transports=1, events=[], steady_state={},
        program_cycle_kpi={"throughput": 9.75}
    )
    assert KPIEngine().calculate(result).transports_per_hour == 9.75
