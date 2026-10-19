from src.model.simulation_state import (
    SimulationState
)

from src.core.event_driven_processor import (
    EventDrivenProcessor
)

from src.model.event import (
    Event
)


def test_hanger_entry_and_exit():

    state = SimulationState()

    processor = EventDrivenProcessor(
        state
    )

    processor.process(
        Event(
            0,
            "HANGER_ENTRY",
            None,
            1,
            None,
            1
        )
    )

    assert 1 in state.active_hangers

    processor.process(
        Event(
            100,
            "HANGER_EXIT",
            None,
            1,
            22,
            None
        )
    )

    assert 1 not in state.active_hangers

    assert (
        state.completed_hangers
        == 1
    )