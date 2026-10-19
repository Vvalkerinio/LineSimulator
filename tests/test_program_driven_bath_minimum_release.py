from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from src.core.program_driven_simulator import ProgramDrivenSimulator
from src.gui.manipulator_trajectory_tab import ManipulatorTrajectoryTab
from src.model.manipulator import Manipulator
from src.model.manipulator_program import ManipulatorProgram
from src.model.manipulator_program_step import ManipulatorProgramStep
from src.model.simulation_configuration import SimulationConfiguration
from src.model.station import Station


def _step(step_no, station_id, action):
    return ManipulatorProgramStep(
        manipulator_id=1,
        step_no=step_no,
        cycle_time_start=0.0,
        cycle_time_end=0.0,
        station_id=station_id,
        plc_station_value=station_id,
        action=action,
        wait_time_01s=0,
        command_name="PICKUP" if action == 1 else "DROP",
    )


def test_program_pickup_waits_until_bath_minimum_process_time():
    configuration = SimulationConfiguration(
        stations=[
            Station(1, "Load", True, 0.0, 0.0, is_process_bath=False),
            Station(2, "Bath", True, 10.0, 30.0),
            Station(3, "Unload", True, 0.0, 0.0, is_process_bath=False),
        ],
        manipulators=[
            Manipulator(
                id=1,
                position=1,
                lift_time=1.0,
                drop_time=1.0,
                travel_time_per_position=1.0,
            )
        ],
    )
    program = ManipulatorProgram(
        manipulator_id=1,
        index_address=500,
        steps=[
            _step(1, 1, ProgramDrivenSimulator.ACTION_PICKUP),
            _step(2, 2, ProgramDrivenSimulator.ACTION_DROP),
            _step(3, 2, ProgramDrivenSimulator.ACTION_PICKUP),
            _step(4, 3, ProgramDrivenSimulator.ACTION_DROP),
        ],
    )

    result = ProgramDrivenSimulator(
        configuration,
        programs={1: program},
        cycles=1,
        initial_state_mode=ProgramDrivenSimulator.INITIAL_STATE_EMPTY,
    ).run()

    bath_drop_finish = next(
        task.end_time
        for task in result.manipulator_tasks
        if task.target_station == 2
    )
    bath_pickup = next(
        record
        for record in result.process_compliance
        if record.station_id == 2
    )
    pickup_execution = next(
        execution
        for execution in result.program_word_executions
        if execution.logical_step_no == 3 and execution.word_kind == "ACTION"
    )

    assert pickup_execution.start_time == bath_drop_finish
    assert pickup_execution.end_time >= bath_drop_finish + 10.0 + 1.0
    assert bath_pickup.actual_time >= 10.0


def test_empty_initial_state_ignores_supplied_station_occupancy():
    configuration = SimulationConfiguration(
        stations=[
            Station(1, "Load", True, 0.0, 0.0),
            Station(2, "Bath", True, 10.0, 30.0),
            Station(3, "Unload", True, 0.0, 0.0),
        ],
        manipulators=[],
    )
    simulator = ProgramDrivenSimulator(
        configuration,
        programs={},
        initial_station_occupancy={2: 1},
        initial_state_mode=ProgramDrivenSimulator.INITIAL_STATE_EMPTY,
    )
    state = {
        "next_hanger_id": 0,
        "station_hangers": {},
        "station_entry_times": {},
        "prefilled_hangers": 0,
    }

    simulator._initial_line_fill(
        result=None,
        state=state,
        load_station=1,
        unload_station=3,
    )

    assert state["station_hangers"] == {}
    assert state["prefilled_hangers"] == 0


def test_completed_manipulator_position_is_held_until_simulation_end():
    configuration = SimulationConfiguration(
        stations=[
            Station(1, "Load", True, 0.0, 0.0, is_process_bath=False),
            Station(2, "Bath", True, 10.0, 30.0),
            Station(3, "Unload", True, 0.0, 0.0, is_process_bath=False),
        ],
        manipulators=[
            Manipulator(1, 1, 1.0, 1.0, 1.0),
            Manipulator(2, 5, 1.0, 1.0, 1.0),
        ],
    )
    programs = {
        1: ManipulatorProgram(
            manipulator_id=1,
            index_address=500,
            steps=[
                _step(1, 1, ProgramDrivenSimulator.ACTION_PICKUP),
            ],
        ),
        2: ManipulatorProgram(
            manipulator_id=2,
            index_address=600,
            steps=[
                _step(1, 3, ProgramDrivenSimulator.ACTION_PICKUP),
            ],
        ),
    }

    result = ProgramDrivenSimulator(
        configuration,
        programs=programs,
        cycles=1,
        initial_state_mode=ProgramDrivenSimulator.INITIAL_STATE_EMPTY,
    ).run()

    hold = next(
        segment
        for segment in result.timeline_segments
        if segment.manipulator_id == 1 and segment.segment_type == "stationary_hold"
    )

    assert hold.start_time == 1.0
    assert hold.end_time == result.final_time == 3.0
    assert hold.start_position == hold.end_position == 1

    class TrajectoryStyleContext:
        SOURCE_OVERLAY = "overlay"

        def _color_for_manipulator(self, _manipulator_id):
            return QColor(40, 110, 220)

        def _source_mode(self):
            return "program"

    pen = ManipulatorTrajectoryTab._style_pen_for_segment(
        TrajectoryStyleContext(),
        hold,
        "program",
    )

    assert pen.style() == Qt.SolidLine
