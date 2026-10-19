from src.model.event import Event

from src.model.simulation_state import (
    SimulationState
)

from src.core.event_processor import (
    EventProcessor
)


class DummyTransport:

    def __init__(self):

        self.hanger_id = 1


def test_transport_registration():

    state = SimulationState()

    processor = EventProcessor(
        state
    )

    transport = DummyTransport()

    processor.register_transport(
        transport
    )

    assert (
        len(
            state.scheduled_transports
        )
        == 1
    )


def test_completed_transport_counter():

    state = SimulationState()

    processor = EventProcessor(
        state
    )

    processor.process(
        Event(
            time=10,
            event_type="MOVE",
            manipulator_id=1,
            hanger_id=1,
            source_station=1,
            target_station=2
        )
    )

    assert (
        state.completed_transports
        == 1
    )