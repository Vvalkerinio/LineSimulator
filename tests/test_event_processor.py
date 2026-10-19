from src.model.event import Event

from src.model.simulation_state import (
    SimulationState
)

from src.core.event_processor import (
    EventProcessor
)


def test_process_move_event():

    state = SimulationState()

    processor = EventProcessor(
        state
    )

    event = Event(
        time=10,
        event_type="MOVE",
        manipulator_id=1,
        hanger_id=7,
        source_station=5,
        target_station=6
    )

    processor.process(
        event
    )

    assert (
        state.current_time
        == 10
    )

    assert (
        state.completed_events
        == 1
    )

    assert (
        state.station_hangers[6]
        == 7
    )

    assert (
        state.manipulator_positions[1]
        == 6
    )
