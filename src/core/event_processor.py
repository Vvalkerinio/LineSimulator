from src.model.event import Event


class EventProcessor:

    def __init__(
        self,
        simulation_state
    ):
        self.simulation_state = (
            simulation_state
        )

    def register_transport(
        self,
        transport
    ) -> None:

        self.simulation_state.scheduled_transports.append(
            transport
        )

    def process(
        self,
        event: Event
    ) -> None:

        self.simulation_state.current_time = (
            event.time
        )

        self.simulation_state.completed_events += 1

        if event.event_type != "MOVE":
            return

        self.simulation_state.completed_transports += 1

        self.simulation_state.station_hangers[
            event.target_station
        ] = event.hanger_id

        self.simulation_state.manipulator_positions[
            event.manipulator_id
        ] = event.target_station