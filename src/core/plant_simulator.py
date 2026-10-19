from src.core.event_engine import EventEngine
from src.core.event_processor import (
    EventProcessor
)
from src.core.process_time_engine import (
    ProcessTimeEngine
)
from src.core.process_violation_engine import (
    ProcessViolationEngine
)
from src.core.hanger_factory import (
    HangerFactory
)

from src.model.event import Event
from src.model.simulation_result import (
    SimulationResult
)
from src.model.simulation_state import (
    SimulationState
)
from src.model.manipulator_task import (
    ManipulatorTask
)


class PlantSimulator:

    def __init__(
        self,
        config,
        context=None,
        route_builder=None,
        services=None
    ):
        self.config = config
        self.context = context
        self.route_builder = route_builder
        self.services = services

        self.engine = EventEngine()

    def _build_route(self):

        recipe = None

        if self.context is not None:
            recipe = getattr(
                self.context,
                "recipe",
                None
            )

        if (
            recipe is not None
            and self.route_builder is not None
        ):
            process_route = (
                self.route_builder.build(
                    recipe
                )
            )

            return [
                station_id
                for station_id in process_route.stations
                if any(
                    s.id == station_id
                    and s.enabled
                    for s in self.config.stations
                )
            ]

        return [
            station.id
            for station
            in self.config.stations
            if station.enabled
        ]

    def run(self):

        route = self._build_route()

        if len(route) < 2:
            return SimulationResult()

        hangers = (
            HangerFactory()
            .create(
                hanger_count=
                    self.config.hanger_count,
                route=route,
                entry_interval=
                    self.config.entry_interval
            )
        )

        fallback_manipulator = (
            self.config.manipulators[0]
        )

        result = SimulationResult()

        result.generated_hangers = (
            len(hangers)
        )

        state = SimulationState()

        processor = EventProcessor(
            state
        )

        process_engine = (
            ProcessTimeEngine()
        )

        violation_engine = (
            ProcessViolationEngine()
        )

        max_finish_time = 0.0

        for hanger in hangers:

            current_time = (
                hanger.entered_station_at
            )

            for index in range(
                len(route) - 1
            ):

                source = route[index]
                target = route[index + 1]

                target_station = next(
                    (
                        station
                        for station
                        in self.config.stations
                        if station.id == target
                    ),
                    None
                )

                if target_station is not None:

                    process_time = (
                        process_engine.process_time(
                            target_station
                        )
                    )

                    actual_time = (
                        process_engine.actual_time(
                            target_station
                        )
                    )

                    violation = (
                        violation_engine.validate(
                            target_station,
                            actual_time
                        )
                    )

                    if violation is not None:

                        result.process_violations.append(
                            violation
                        )

                    current_time += (
                        process_time
                    )

                    result.total_process_time += (
                        process_time
                    )

                duration = (
                    fallback_manipulator.lift_time
                    + fallback_manipulator.travel_time(
                        source,
                        target
                    )
                    + fallback_manipulator.drop_time
                )

                current_time += duration

                scheduled = None

                if (
                    self.services is not None
                    and self.services.transport_scheduler
                    is not None
                ):
                    scheduled = (
                        self.services
                        .transport_scheduler
                        .schedule(
                            hanger_id=hanger.id,
                            source_station=source,
                            target_station=target,
                            current_time=current_time
                        )
                    )

                if scheduled is not None:

                    processor.register_transport(
                        scheduled
                    )

                    result.manipulator_tasks.append(
                        ManipulatorTask(
                            manipulator_id=
                                scheduled.manipulator_id,
                            hanger_id=
                                hanger.id,
                            source_station=
                                source,
                            target_station=
                                target,
                            start_time=
                                scheduled.start_time,
                            end_time=
                                scheduled.finish_time
                        )
                    )

                    event = Event(
                        scheduled.finish_time,
                        "MOVE",
                        scheduled.manipulator_id,
                        hanger.id,
                        source,
                        target
                    )

                else:

                    task_start = (
                        current_time
                        - duration
                    )

                    result.manipulator_tasks.append(
                        ManipulatorTask(
                            manipulator_id=
                                fallback_manipulator.id,
                            hanger_id=
                                hanger.id,
                            source_station=
                                source,
                            target_station=
                                target,
                            start_time=
                                task_start,
                            end_time=
                                current_time
                        )
                    )

                    event = Event(
                        current_time,
                        "MOVE",
                        fallback_manipulator.id,
                        hanger.id,
                        source,
                        target
                    )

                max_finish_time = max(
                    max_finish_time,
                    event.time
                )

                self.engine.schedule(
                    event
                )

        while self.engine.has_events():

            event = self.engine.pop()

            processor.process(
                event
            )

            result.events.append(
                event
            )

        result.final_time = (
            max_finish_time
        )

        result.processed_events = (
            state.completed_events
        )

        result.scheduled_transports = len(
            state.scheduled_transports
        )

        result.completed_transports = (
            state.completed_transports
        )

        return result