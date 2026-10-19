import pytest

from src.core.program_driven_simulator import ProgramDrivenSimulator
from src.model.event import Event
from src.model.event_type import EventType
from src.model.program_word_execution import ProgramWordExecution
from src.model.simulation_configuration import SimulationConfiguration
from src.model.simulation_result import SimulationResult


def execution(cycle_no, start, end):
    return ProgramWordExecution(
        manipulator_id=1,
        cycle_no=cycle_no,
        plc_index=1,
        word_address=501,
        logical_step_no=1,
        word_kind="STATION",
        word_value=1,
        start_time=start,
        end_time=end,
        start_position=1,
        end_position=1,
        action=2
    )


def exit_event(time_value, hanger_id):
    return Event(
        time=time_value,
        event_type=EventType.HANGER_EXIT,
        manipulator_id=4,
        hanger_id=hanger_id,
        source_station=22,
        target_station=22
    )


def test_two_hangers_per_865_second_cycle_is_8_32_per_hour():
    configuration = SimulationConfiguration(
        stations=[],
        manipulators=[]
    )
    simulator = ProgramDrivenSimulator(
        configuration=configuration,
        programs={}
    )
    result = SimulationResult()
    result.program_word_executions = [
        execution(1, 0.0, 865.0),
        execution(2, 865.0, 1730.0),
        execution(3, 1730.0, 2595.0)
    ]
    result.events = [
        exit_event(800.0, 1),
        exit_event(810.0, 2),
        exit_event(1600.0, 3),
        exit_event(1610.0, 4),
        exit_event(2460.0, 5),
        exit_event(2470.0, 6)
    ]

    audit = simulator._calculate_program_cycle_throughput(result)

    assert audit["excluded_warmup_cycles"] == 1
    assert audit["complete_cycles"] == 2
    assert audit["cycle_duration"] == pytest.approx(865.0)
    assert audit["hangers_per_cycle"] == pytest.approx(2.0)
    assert audit["throughput"] == pytest.approx(2 * 3600 / 865)
