from src.model.event import Event


class EventDrivenProcessor:

    def __init__(
        self,
        simulation_state
    ):
        self.simulation_state = (
            simulation_state
        )

    def process(
        self,
        event: Event
    ) -> None:

        self.simulation_state.current_time = (
            event.time
        )

        self.simulation_state.completed_events += 1

        if (
            event.event_type
            == "HANGER_ENTRY"
        ):

            self.simulation_state.active_hangers.add(
                event.hanger_id
            )

            self.simulation_state.hanger_positions[
                event.hanger_id
            ] = event.target_station

            return

        if (
            event.event_type
            == "PROCESS_END"
        ):

            self.simulation_state.hanger_positions[
                event.hanger_id
            ] = event.target_station

            return

        if (
            event.event_type
            == "TRANSPORT_END"
        ):

            self.simulation_state.completed_transports += 1

            self.simulation_state.hanger_positions[
                event.hanger_id
            ] = event.target_station

            return

        if (
            event.event_type
            == "RETRY_TRANSPORT"
        ):
            return

        if (
            event.event_type
            == "HANGER_EXIT"
        ):

            self.simulation_state.active_hangers.discard(
                event.hanger_id
            )

            self.simulation_state.completed_hangers += 1

            return
