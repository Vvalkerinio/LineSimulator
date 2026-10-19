from pathlib import Path

from src.analysis.kpi_engine import KPIEngine
from src.io.configuration_serializer import (
    configuration_from_dict,
    configuration_to_dict,
    create_default_configuration,
)
from src.model.event import Event
from src.model.event_type import EventType
from src.model.simulation_result import SimulationResult


def exit_event(time_value, hanger_id):
    return Event(time_value, EventType.HANGER_EXIT, None, hanger_id, 21, 22)


def result_with_exits(*times):
    result = SimulationResult()
    result.events = [exit_event(value, index + 1) for index, value in enumerate(times)]
    result.final_time = max(times) if times else 0.0
    result.processed_events = len(result.events)
    result.completed_transports = len(times)
    result.steady_state = {"analysis_start": 0.0, "analysis_end": result.final_time + 1.0}
    return result


def test_transport_rate_is_exit_interval_and_parts_are_multiplied():
    result = result_with_exits(0.0, 300.0, 600.0)
    kpi = KPIEngine().calculate(result, pieces_per_transport=7)
    assert kpi.transports_per_hour == 12.0
    assert kpi.parts_per_hour == 84.0
    assert kpi.average_cycle_time == 300.0


def test_program_cycle_metadata_does_not_replace_physical_exit_rate():
    result = result_with_exits(0.0, 300.0, 600.0)
    result.program_cycle_kpi = {
        "cycle_duration": 100.0,
        "hangers_per_cycle": 2.0,
        "throughput": 72.0,
    }
    kpi = KPIEngine().calculate(result, pieces_per_transport=7)
    assert kpi.transports_per_hour == 12.0
    assert kpi.parts_per_hour == 84.0


def test_old_json_defaults_to_seven_and_new_json_roundtrips():
    config = create_default_configuration()
    data = configuration_to_dict(config)
    data.pop("pieces_per_transport", None)
    loaded = configuration_from_dict(data)
    assert loaded.pieces_per_transport == 7
    loaded.pieces_per_transport = 9
    assert configuration_from_dict(configuration_to_dict(loaded)).pieces_per_transport == 9


def test_event_residence_ends_at_physical_lift_start():
    source = Path("src/core/event_driven_simulator.py").read_text(encoding="utf-8")
    assert "actual_time = scheduled.pickup_finish_time - entry_time" in source
    assert "exit_time=scheduled.pickup_finish_time" in source
    assert "actual_time = scheduled.pickup_start_time - entry_time" not in source


def test_results_tab_has_compact_kpi_and_details_group():
    source = Path("src/gui/results_tab.py").read_text(encoding="utf-8")
    assert 'QGroupBox("KPI")' in source
    assert 'QGroupBox("Szczegóły symulacji")' in source
    assert "Precise Event Throughput - Ilość szt/h" in source
    assert "Precise Event Throughput - Ilość transportów/h" in source
    assert '"Cycle Time [s]"' in source
    assert '"Process Violations"' in source
    assert '"Manipulator Separation"' in source
