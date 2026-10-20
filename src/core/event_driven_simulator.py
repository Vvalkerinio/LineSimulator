import math
from bisect import bisect_left, bisect_right

from src.core.simulation_debug import debug_print
from src.core.simulation_preflight import SimulationPreflightValidator
from src.core.event_engine import EventEngine
from src.core.process_limit_classifier import assess_process_time
from src.core.event_driven_processor import EventDrivenProcessor
from src.core.hanger_factory import HangerFactory
from src.core.process_time_engine import ProcessTimeEngine
from src.core.simulation_services_factory import SimulationServicesFactory
from src.core.station_manager import StationManager
from src.core.station_queue_manager import StationQueueManager
from src.core.entry_queue_manager import EntryQueueManager
from src.core.deadlock_detector import DeadlockDetector
from src.core.event_driven_passing_detector import EventDrivenPassingDetector
from src.core.shared_bath_group_builder import SharedBathGroupBuilder
from src.core.shared_bath_selector import SharedBathSelector
from src.core.station_reservation_service import StationReservationService
from src.core.deadline_aware_transport import DeadlineAwareTransport
from src.core.predictive_pickup_scheduler import PredictivePickupScheduler
from src.model.event import Event
from src.model.event_type import EventType
from src.model.simulation_result import SimulationResult
from src.model.simulation_state import SimulationState
from src.model.manipulator_task import ManipulatorTask
from src.model.waiting_transport import WaitingTransport
from src.model.manipulator_timeline_segment import ManipulatorTimelineSegment
from src.model.start_mode import StartMode
from src.model.process_compliance_record import ProcessComplianceRecord
from src.analysis.steady_state_detector import SteadyStateDetector
from src.core.yield_timeline_integrator import YieldTimelineIntegrator

class EventDrivenSimulator:
    RETRY_INTERVAL = 30.0

    def __init__(self, config, services=None, progress_callback=None):
        self.config = config
        self.services = services
        self.engine = EventEngine()
        self.progress_callback = progress_callback
        self._last_progress_percent = -1

    def _route(self):
        route = []
        processed_groups = set()
        for station in self.config.stations:
            if not station.enabled:
                continue
            group = getattr(station, 'shared_bath_group', None)
            if group is None or str(group).strip() == '' or str(group).strip().lower() == 'none':
                route.append(station.id)
                continue
            group = str(group).strip()
            if group in processed_groups:
                continue
            processed_groups.add(group)
            route.append(station.id)
        return route

    def _services(self):
        if self.services is not None:
            return self.services
        return SimulationServicesFactory.create(
            self.config.manipulators,
            self.config.stations
        )

    def _configure_transport_engine(self, services):
        spacing = float(getattr(self.config, 'minimum_manipulator_spacing', 0.0))
        try:
            selector = services.transport_scheduler.assignment_selector
            transport_engine = selector.transport_engine
            transport_engine.minimum_manipulator_spacing = spacing
            debug_print(lambda: f'MINIMUM MANIPULATOR SPACING {spacing}')
        except AttributeError:
            debug_print(lambda: 'MINIMUM MANIPULATOR SPACING not applied')

    def _create_hangers(self, route):
        factory = HangerFactory()
        if getattr(self.config, 'infinite_feed', False):
            return factory.create_for_duration(route=route, feed_duration=self.config.feed_duration, entry_interval=self.config.entry_interval)
        return factory.create(hanger_count=self.config.hanger_count, route=route, entry_interval=self.config.entry_interval)

    def _select_shared_bath_target(self, next_station, shared_bath_selector, event_time):
        debug_print(lambda: ' '.join([str('SHARED_BATH_CHECK'), str(next_station)]))
        for group in getattr(self.config, 'shared_bath_groups', []):
            debug_print(lambda: ' '.join([str('GROUP'), str(group.group_id), str(group.station_ids)]))
            if next_station not in group.station_ids:
                continue
            selected = shared_bath_selector.select(group.station_ids, event_time)
            recommended_time = float(event_time)
            if hasattr(shared_bath_selector, 'recommended_time'):
                recommended_time = float(shared_bath_selector.recommended_time())
            if selected is None:
                earliest_group_time = shared_bath_selector.earliest_group_availability(group.station_ids, event_time)
                if earliest_group_time is not None:
                    recommended_time = max(recommended_time, float(earliest_group_time))
                if recommended_time <= float(event_time):
                    recommended_time = float(event_time) + self.RETRY_INTERVAL
            debug_print(lambda: ' '.join([str('SELECTED'), str(selected), str('AT'), str(f'{recommended_time:.1f}')]))
            return (selected, recommended_time)
        return (next_station, event_time)

    def _append_idle_segment(self, result, manipulator, last_time, last_position, next_time):
        if next_time <= last_time:
            return
        result.timeline_segments.append(ManipulatorTimelineSegment(manipulator_id=manipulator.id, start_time=last_time, end_time=next_time, start_position=last_position, end_position=last_position, segment_type='idle'))

    def _append_motion_segments(self, result, manipulator, scheduled, last_position):
        if last_position != scheduled.source_station:
            result.timeline_segments.append(ManipulatorTimelineSegment(manipulator_id=manipulator.id, start_time=scheduled.pickup_start_time, end_time=scheduled.pickup_finish_time, start_position=last_position, end_position=scheduled.source_station, segment_type='empty_move'))
        travel_end=min(float(scheduled.transport_finish_time),float(scheduled.transport_start_time)+abs(float(scheduled.target_station)-float(scheduled.source_station))*float(manipulator.travel_time_per_position))
        result.timeline_segments.append(ManipulatorTimelineSegment(manipulator_id=manipulator.id, start_time=scheduled.transport_start_time, end_time=travel_end, start_position=scheduled.source_station, end_position=scheduled.target_station, segment_type='loaded_move', hanger_id=scheduled.hanger_id, pickup_time=scheduled.pickup_finish_time, drop_time=scheduled.transport_finish_time))
        if scheduled.transport_finish_time > travel_end:
            result.timeline_segments.append(ManipulatorTimelineSegment(manipulator_id=manipulator.id, start_time=travel_end, end_time=scheduled.transport_finish_time, start_position=scheduled.target_station, end_position=scheduled.target_station, segment_type='drop_hold', hanger_id=scheduled.hanger_id))
        if scheduled.return_finish_time > scheduled.return_start_time:
            result.timeline_segments.append(ManipulatorTimelineSegment(manipulator_id=manipulator.id, start_time=scheduled.return_start_time, end_time=scheduled.return_finish_time, start_position=scheduled.target_station, end_position=scheduled.return_position, segment_type='return_move'))

    def _finalize_steady_state(self, result):
        detector = SteadyStateDetector()
        analysis_end = None
        if getattr(self.config, 'infinite_feed', False):
            analysis_end = self.config.feed_duration
        analysis_start = getattr(self.config, 'warmup_time', 0.0)
        result.steady_state = detector.detect(result=result, window_size=getattr(self.config, 'steady_state_window', 600.0), analysis_start=analysis_start, analysis_end=analysis_end)
        if result.steady_state is not None:
            result.throughput_windows = result.steady_state.get('windows', [])
            debug_print(lambda: ' '.join([str('STEADY STATE:'), str(result.steady_state)]))
        else:
            result.throughput_windows = []
            debug_print(lambda: 'STEADY STATE: not detected')

    def _prefill_active_baths(self, route, state, station_manager, station_map, process_engine, result, next_hanger_id):
        start_mode = StartMode.from_value(getattr(self.config, 'start_mode', StartMode.EMPTY))
        if start_mode != StartMode.ACTIVE_BATHS:
            return next_hanger_id
        if len(route) < 3:
            return next_hanger_id
        debug_print(lambda: 'START_MODE ACTIVE_BATHS')
        active_process_route = route[1:-1]
        for station_id in active_process_route:
            hanger_id = next_hanger_id
            next_hanger_id += 1
            state.hanger_route_index[hanger_id] = route.index(station_id)
            station = station_map[station_id]
            process_time = process_engine.process_time(station)
            result.total_process_time += process_time
            station_manager.occupy(station_id=station_id, hanger_id=hanger_id, occupied_until=process_time)
            state.station_entry_times[hanger_id, station_id] = 0.0
            self.engine.schedule(Event(process_time, EventType.PROCESS_END, None, hanger_id, station_id, station_id))
            debug_print(lambda: f'PREFILL H={hanger_id} S={station_id} process_end={process_time:.1f}')
        return next_hanger_id

    def run(self):
        SimulationPreflightValidator().validate(self.config)
        services = self._services()
        self._configure_transport_engine(services)
        route = self._route()
        result = SimulationResult()
        last_manipulator_state = {}
        for manipulator in self.config.manipulators:
            last_manipulator_state[manipulator.id] = (0.0, manipulator.position)
        if len(route) < 2:
            return result
        hangers = self._create_hangers(route)
        station_map = {station.id: station for station in self.config.stations}
        self.config.shared_bath_groups = SharedBathGroupBuilder().build(self.config.stations)
        debug_print(lambda: ' '.join([str('SHARED_BATH_GROUPS:'), str([(group.group_id, group.station_ids) for group in self.config.shared_bath_groups])]))
        station_manager = StationManager(self.config.stations)
        station_reservation_service = StationReservationService()
        if hasattr(services.transport_scheduler, 'set_station_reservation_service'):
            services.transport_scheduler.set_station_reservation_service(station_reservation_service)
        shared_bath_selector = SharedBathSelector(station_manager, station_reservation_service)
        queue_manager = StationQueueManager()
        entry_queue = EntryQueueManager()
        deadlock_detector = DeadlockDetector(max_wait_time=300)
        state = SimulationState()
        deadline_transport = DeadlineAwareTransport(station_map=station_map, station_entry_times=state.station_entry_times)
        predictive_pickup = PredictivePickupScheduler(config=self.config, route=route, station_map=station_map, engine=self.engine, state=state)
        predictive_scheduled_pickups = set()
        timeline_segments_by_manipulator = {
            int(manipulator.id): [] for manipulator in self.config.manipulators
        }
        timeline_segment_starts = {
            int(manipulator.id): [] for manipulator in self.config.manipulators
        }
        timeline_segment_prefix_ends = {
            int(manipulator.id): [] for manipulator in self.config.manipulators
        }
        # One hanger/source may have several queued wake-up events, but only
        # one physical transport may ever be committed for that route leg.
        active_transport_keys = set()
        completed_transport_keys = set()
        processor = EventDrivenProcessor(state)
        process_engine = ProcessTimeEngine()
        passing_detector = EventDrivenPassingDetector(services.trajectory_manager, services.manipulator_manager)
        deferred_transports = {}
        last_deferred_wake_time = {'value': None}
        max_factory_hanger_id = 0
        for hanger in hangers:
            max_factory_hanger_id = max(max_factory_hanger_id, hanger.id)
        next_prefill_hanger_id = max_factory_hanger_id + 1
        next_prefill_hanger_id = self._prefill_active_baths(route=route, state=state, station_manager=station_manager, station_map=station_map, process_engine=process_engine, result=result, next_hanger_id=next_prefill_hanger_id)
        result.generated_hangers = len(hangers) + (next_prefill_hanger_id - max_factory_hanger_id - 1)

        def defer_transport(hanger_id: int, manipulator_id: int | None, source_station: int, target_station: int, current_time: float, reason: str, ready_at: float | None = None):
            effective_ready_at = max(
                float(current_time),
                float(current_time if ready_at is None else ready_at)
            )
            existing = deferred_transports.get(hanger_id)
            if existing is not None:
                existing.ready_at = max(float(existing.ready_at), effective_ready_at)
                return
            deferred_transports[hanger_id] = WaitingTransport(hanger_id=hanger_id, manipulator_id=manipulator_id if manipulator_id is not None else -1, source_station=source_station, target_station=target_station, requested_at=current_time, ready_at=effective_ready_at, process_time=0.0)
            deadline_description = deadline_transport.describe(hanger_id=hanger_id, station_id=source_station, current_time=current_time)
            debug_print(lambda: f'DEFERRED H={hanger_id} {source_station}->{target_station} T={current_time:.1f} reason={reason} {deadline_description}')
        shared_bath_retry_counts = {}
        shared_bath_retry_stats = {
            'executed': 0,
            'avoided_intervals': 0,
            'total_delay': 0.0,
        }
        max_shared_bath_retries = max(1, int(getattr(self.config, 'event_driven_max_shared_bath_retries', 200)))

        def index_timeline_segment(segment):
            manipulator_id = int(segment.manipulator_id)
            segments = timeline_segments_by_manipulator.setdefault(
                manipulator_id, []
            )
            starts = timeline_segment_starts.setdefault(manipulator_id, [])
            prefix_ends = timeline_segment_prefix_ends.setdefault(
                manipulator_id, []
            )
            start_time = float(segment.start_time)
            index = bisect_right(starts, start_time)
            segments.insert(index, segment)
            starts.insert(index, start_time)
            prefix_end = (
                prefix_ends[index - 1] if index else float('-inf')
            )
            prefix_ends.insert(
                index, max(prefix_end, float(segment.end_time))
            )
            for position in range(index + 1, len(segments)):
                prefix_ends[position] = max(
                    prefix_ends[position - 1],
                    float(segments[position].end_time),
                )

        def schedule_shared_bath_retry(event, retry_time, reason):
            retry_key = (int(event.hanger_id) if event.hanger_id is not None else -1, int(event.target_station) if event.target_station is not None else -1, str(reason))
            retry_count = shared_bath_retry_counts.get(retry_key, 0) + 1
            shared_bath_retry_counts[retry_key] = retry_count
            if retry_count > max_shared_bath_retries:
                result.deadlocks.append({'type': 'SHARED_BATH_RETRY_LIMIT', 'hanger_id': event.hanger_id, 'station_id': event.target_station, 'time': float(event.time), 'retry_count': retry_count - 1, 'reason': str(reason)})
                result.shared_bath_retry_limit_reached = True
                return False
            current_time = float(event.time)
            try:
                retry_time = float(retry_time)
            except Exception:
                retry_time = current_time + self.RETRY_INTERVAL
            if not math.isfinite(retry_time):
                retry_time = current_time + self.RETRY_INTERVAL
            retry_time = max(retry_time, current_time + 1.0)
            retry_delay = retry_time - current_time
            shared_bath_retry_stats['executed'] += 1
            shared_bath_retry_stats['total_delay'] += retry_delay
            shared_bath_retry_stats['avoided_intervals'] += max(
                0,
                int(retry_delay // self.RETRY_INTERVAL) - 1
            )
            self.engine.schedule(Event(retry_time, EventType.PROCESS_END, event.manipulator_id, event.hanger_id, event.source_station, event.target_station))
            debug_print(lambda: f'SHARED_BATH_RETRY_SCHEDULED H={event.hanger_id} S={event.target_station} current={current_time:.1f} retry_at={retry_time:.1f} interval={self.RETRY_INTERVAL:.1f} reason={reason}')
            return True

        def proposal_respects_full_spacing(scheduled, manipulator, last_position):
            travel_end = min(
                float(scheduled.transport_finish_time),
                float(scheduled.transport_start_time)
                + abs(
                    float(scheduled.target_station)
                    - float(scheduled.source_station)
                ) * float(manipulator.travel_time_per_position)
            )
            phases = (
                (
                    scheduled.pickup_start_time,
                    scheduled.pickup_finish_time,
                    last_position,
                    scheduled.source_station,
                ),
                (
                    scheduled.pickup_finish_time,
                    scheduled.transport_start_time,
                    scheduled.source_station,
                    scheduled.source_station,
                ),
                (
                    scheduled.transport_start_time,
                    travel_end,
                    scheduled.source_station,
                    scheduled.target_station,
                ),
                (
                    travel_end,
                    scheduled.transport_finish_time,
                    scheduled.target_station,
                    scheduled.target_station,
                ),
                (
                    scheduled.return_start_time,
                    scheduled.return_finish_time,
                    scheduled.target_station,
                    scheduled.return_position,
                ),
            )
            required = float(self.config.minimum_manipulator_spacing)
            manipulator_id = int(manipulator.id)
            neighbors = (manipulator_id - 1, manipulator_id + 1)

            def position_at(start_position, end_position, start_time, end_time, time):
                if float(end_time) <= float(start_time):
                    return float(end_position)
                ratio = max(
                    0.0,
                    min(
                        1.0,
                        (float(time) - float(start_time))
                        / (float(end_time) - float(start_time)),
                    ),
                )
                return float(start_position) + (
                    float(end_position) - float(start_position)
                ) * ratio

            for phase_start, phase_end, start_position, end_position in phases:
                phase_start = float(phase_start)
                phase_end = float(phase_end)
                for neighbor_id in neighbors:
                    other_segments = timeline_segments_by_manipulator.get(
                        neighbor_id, ()
                    )
                    starts = timeline_segment_starts.get(neighbor_id, ())
                    prefix_ends = timeline_segment_prefix_ends.get(
                        neighbor_id, ()
                    )
                    stop = bisect_right(starts, phase_end)
                    begin = bisect_left(
                        prefix_ends, phase_start, 0, stop
                    )
                    for index in range(begin, stop):
                        other = other_segments[index]
                        other_start = float(other.start_time)
                        other_end = float(other.end_time)
                        overlap_start = max(phase_start, other_start)
                        overlap_end = min(phase_end, other_end)
                        if overlap_end + 1e-9 < overlap_start:
                            continue
                        for time in (overlap_start, overlap_end):
                            mine = position_at(
                                start_position,
                                end_position,
                                phase_start,
                                phase_end,
                                time,
                            )
                            theirs = position_at(
                                other.start_position,
                                other.end_position,
                                other_start,
                                other_end,
                                time,
                            )
                            gap = (
                                mine - theirs
                                if neighbor_id < manipulator_id
                                else theirs - mine
                            )
                            if gap + 1e-9 < required:
                                return False
            return True

        def commit_scheduled_transport(scheduled, event_time: float, delayed_by_queue: bool=False, delayed_by_no_passing: bool=False) -> bool:
            transport_key = (int(scheduled.hanger_id), int(scheduled.source_station))
            if transport_key in active_transport_keys or transport_key in completed_transport_keys:
                debug_print(lambda: f'DUPLICATE_TRANSPORT_COMMIT_SKIPPED H={scheduled.hanger_id} S={scheduled.source_station}')
                return True
            # The hanger must still physically occupy the claimed source.
            if station_manager.state(
                int(scheduled.source_station)
            ).hanger_id != int(scheduled.hanger_id):
                debug_print(lambda: f'STALE_TRANSPORT_COMMIT_SKIPPED H={scheduled.hanger_id} S={scheduled.source_station}')
                return True
            manipulator = services.manipulator_manager.get(scheduled.manipulator_id)
            last_time, last_position = last_manipulator_state[manipulator.id]
            assignment_engine = services.transport_scheduler.assignment_selector.transport_engine
            if not proposal_respects_full_spacing(scheduled, manipulator, last_position):
                retry_at=max(float(event_time)+self.RETRY_INTERVAL,float(scheduled.pickup_start_time))
                defer_transport(hanger_id=scheduled.hanger_id, manipulator_id=scheduled.manipulator_id, source_station=scheduled.source_station, target_station=scheduled.target_station, current_time=event_time, reason='FULL_SPACING_BLOCKED', ready_at=retry_at)
                self.engine.schedule(Event(retry_at, EventType.QUEUE_RELEASE, None, None, None, scheduled.source_station))
                return False
            if not assignment_engine.validate_static_occupancy(
                manipulator, last_position,
                scheduled.source_station, scheduled.target_station,
                scheduled.pickup_start_time, scheduled.pickup_finish_time,
                scheduled.transport_start_time, scheduled.transport_finish_time,
                scheduled.return_position, scheduled.return_start_time,
                scheduled.return_finish_time
            ):
                yield_move = assignment_engine.try_plan_yield(
                    blocked_target=scheduled.source_station,
                    current_time=event_time
                )
                # schedule() may already have committed one or more YIELDs.
                # Do not wake the deferred predictive pickup before every
                # currently active YIELD relevant to this planning instant is
                # complete, otherwise a premature wake recomputes an already
                # late pickup and creates a hard max violation downstream of
                # shared bath.
                yield_moves = list(getattr(
                    getattr(assignment_engine, 'yield_planner', None),
                    'moves',
                    []
                ))
                if yield_move is not None:
                    yield_moves.append(yield_move)
                future_yield_ends = [
                    float(move.end_time)
                    for move in yield_moves
                    if float(move.end_time) > float(event_time)
                ]
                retry_at = (
                    max(future_yield_ends)
                    if future_yield_ends
                    else float(event_time) + self.RETRY_INTERVAL
                )
                defer_transport(
                    hanger_id=scheduled.hanger_id,
                    manipulator_id=scheduled.manipulator_id,
                    source_station=scheduled.source_station,
                    target_station=scheduled.target_station,
                    current_time=event_time,
                    reason='TRACK_REVALIDATION_YIELD' if future_yield_ends else 'TRACK_REVALIDATION_BLOCKED',
                    ready_at=retry_at
                )
                self.engine.schedule(Event(
                    retry_at, EventType.QUEUE_RELEASE,
                    None, None, None, scheduled.source_station
                ))
                return False
            passing_ok = passing_detector.transport_allowed(manipulator_id=manipulator.id, start_position=last_position, target_position=scheduled.target_station, start_time=scheduled.pickup_start_time, finish_time=scheduled.return_finish_time)
            if not passing_ok:
                defer_transport(hanger_id=scheduled.hanger_id, manipulator_id=scheduled.manipulator_id, source_station=scheduled.source_station, target_station=scheduled.target_station, current_time=event_time, reason='NO_PASSING_BLOCKED')
                return False
            target_can_be_reserved = services.transport_scheduler.reserve_target_station(hanger_id=scheduled.hanger_id, target_station=scheduled.target_station, drop_time=scheduled.transport_finish_time)
            if not target_can_be_reserved:
                defer_transport(hanger_id=scheduled.hanger_id, manipulator_id=scheduled.manipulator_id, source_station=scheduled.source_station, target_station=scheduled.target_station, current_time=event_time, reason='TARGET_STATION_RESERVED')
                return False
            services.transport_scheduler.assignment_selector.availability.reserve(
                scheduled.manipulator_id, scheduled.return_finish_time
            )
            services.transport_scheduler.release_source_station_at_pickup(hanger_id=scheduled.hanger_id, source_station=scheduled.source_station, pickup_time=scheduled.pickup_finish_time)
            first_new_segment = len(result.timeline_segments)
            self._append_idle_segment(result, manipulator, last_time, last_position, scheduled.pickup_start_time)
            self._append_motion_segments(result, manipulator, scheduled, last_position)
            for segment in result.timeline_segments[first_new_segment:]:
                index_timeline_segment(segment)
            if last_position != scheduled.source_station:
                services.track_service.reserve(manipulator_id=manipulator.id, source_station=last_position, target_station=scheduled.source_station, start_time=scheduled.pickup_start_time, travel_time_per_position=manipulator.travel_time_per_position)
            services.track_service.reserve(manipulator_id=manipulator.id, source_station=scheduled.source_station, target_station=scheduled.target_station, start_time=scheduled.transport_start_time, travel_time_per_position=manipulator.travel_time_per_position)
            services.trajectory_manager.add_move(manipulator_id=manipulator.id, start_position=last_position, end_position=scheduled.source_station, start_time=scheduled.pickup_start_time, travel_time_per_position=manipulator.travel_time_per_position)
            if scheduled.return_finish_time > scheduled.return_start_time:
                services.track_service.reserve(manipulator_id=manipulator.id, source_station=scheduled.target_station, target_station=scheduled.return_position, start_time=scheduled.return_start_time, travel_time_per_position=manipulator.travel_time_per_position)
            services.trajectory_manager.add_move(manipulator_id=manipulator.id, start_position=scheduled.source_station, end_position=scheduled.target_station, start_time=scheduled.transport_start_time, travel_time_per_position=manipulator.travel_time_per_position)
            if scheduled.return_finish_time > scheduled.return_start_time:
                services.trajectory_manager.add_move(manipulator_id=manipulator.id, start_position=scheduled.target_station, end_position=scheduled.return_position, start_time=scheduled.return_start_time, travel_time_per_position=manipulator.travel_time_per_position)
            manipulator.position = scheduled.return_position
            last_manipulator_state[manipulator.id] = (scheduled.return_finish_time, scheduled.return_position)
            entry_time = state.station_entry_times.get((scheduled.hanger_id, scheduled.source_station))
            process_end_time = state.pending_process_end_times.get((scheduled.hanger_id, scheduled.source_station))
            if entry_time is not None and process_end_time is not None:
                station = station_map[scheduled.source_station]
                actual_time = scheduled.pickup_finish_time - entry_time
                assessment = assess_process_time(station, actual_time)
                min_ok = assessment.nominal_min_ok
                max_ok = assessment.nominal_max_ok
                violation_type = assessment.status
                if assessment.hard_violation:
                    debug_print(lambda: f'PROCESS_HARD_VIOLATION H={scheduled.hanger_id} S={scheduled.source_station} actual={actual_time:.1f} possible_min={station.possible_min_process_time:.1f} possible_max={station.possible_max_process_time:.1f} status={assessment.status}')
                result.process_compliance.append(ProcessComplianceRecord(hanger_id=scheduled.hanger_id, station_id=scheduled.source_station, entry_time=entry_time, exit_time=scheduled.pickup_finish_time, actual_time=actual_time, min_time=station.min_process_time, max_time=station.max_process_time, min_ok=min_ok, max_ok=max_ok, violation_type=violation_type, possible_min_time=float(station.possible_min_process_time), possible_max_time=float(station.possible_max_process_time), possible_min_ok=assessment.possible_min_ok, possible_max_ok=assessment.possible_max_ok, compliance_status=assessment.status, nominal_deviation=assessment.nominal_deviation))
            debug_print(lambda: f'PICKUP H={scheduled.hanger_id} S={scheduled.source_station} M={scheduled.manipulator_id} pickup_start={scheduled.pickup_start_time:.1f} pickup_finish={scheduled.pickup_finish_time:.1f}')
            result.manipulator_tasks.append(ManipulatorTask(manipulator_id=scheduled.manipulator_id, hanger_id=scheduled.hanger_id, source_station=scheduled.source_station, target_station=scheduled.target_station, start_time=scheduled.pickup_start_time, end_time=scheduled.return_finish_time, wait_time=max(0.0, scheduled.pickup_start_time - event_time), delayed_by_queue=delayed_by_queue, delayed_by_no_passing=delayed_by_no_passing))
            active_transport_keys.add(transport_key)
            predictive_scheduled_pickups.add(transport_key)
            deferred_transports.pop(int(scheduled.hanger_id), None)
            self.engine.schedule(Event(scheduled.transport_finish_time, EventType.TRANSPORT_END, scheduled.manipulator_id, scheduled.hanger_id, scheduled.source_station, scheduled.target_station))
            debug_print(lambda: f'TASK H={scheduled.hanger_id} M={scheduled.manipulator_id} {scheduled.source_station}->{scheduled.target_station} pickup={scheduled.pickup_finish_time:.1f} drop={scheduled.transport_finish_time:.1f}')
            debug_print(lambda: f'ASSIGN M={scheduled.manipulator_id} {scheduled.source_station}->{scheduled.target_station} finish={scheduled.return_finish_time:.1f}')
            debug_print(lambda: f'M={scheduled.manipulator_id} pickup={scheduled.pickup_finish_time:.1f} source={scheduled.source_station}')
            return True

        def earlier_deadline_waiting_for_target(hanger_id: int, target_station: int, latest_pickup_time):
            if latest_pickup_time is None:
                return None
            candidates = []
            for waiting in deferred_transports.values():
                if int(waiting.hanger_id) == int(hanger_id) or int(waiting.target_station) != int(target_station):
                    continue
                waiting_latest = deadline_transport.latest_pickup_time(waiting.hanger_id, waiting.source_station)
                if waiting_latest is not None and float(waiting_latest) < float(latest_pickup_time) - 1e-9:
                    candidates.append((float(waiting_latest), int(waiting.hanger_id), waiting))
            return min(candidates, default=None, key=lambda item: (item[0], item[1]))

        def commit_selector_yield(current_time: float, wake_station: int | None):
            selector = services.transport_scheduler.assignment_selector
            proposal = selector.consume_pending_yield_proposal()
            if proposal is None:
                return None
            move = selector.transport_engine.commit_yield(proposal)
            if move is not None:
                self.engine.schedule(Event(
                    float(move.end_time), EventType.QUEUE_RELEASE,
                    None, None, None, wake_station
                ))
                debug_print(lambda: f'YIELD_WAKE_SCHEDULED T={float(move.end_time):.1f} S={wake_station}')
            return move

        def wake_deferred_transports(current_time: float, reason: str):
            if not deferred_transports:
                return
            if last_deferred_wake_time['value'] == current_time:
                return
            last_deferred_wake_time['value'] = current_time
            debug_print(lambda: f'WAKE DEFERRED count={len(deferred_transports)} T={current_time:.1f} reason={reason}')
            ordered_waiting = sorted(list(deferred_transports.items()), key=lambda item: deadline_transport.priority_key(hanger_id=item[1].hanger_id, station_id=item[1].source_station, current_time=current_time))
            for hanger_id, waiting in ordered_waiting:
                if float(current_time) + 1e-9 < float(waiting.ready_at):
                    continue
                latest_pickup_time = deadline_transport.latest_pickup_time(hanger_id=waiting.hanger_id, station_id=waiting.source_station)
                scheduled = services.transport_scheduler.schedule(hanger_id=waiting.hanger_id, source_station=waiting.source_station, target_station=waiting.target_station, current_time=current_time, latest_pickup_time=latest_pickup_time)
                if scheduled is None:
                    move = commit_selector_yield(current_time, waiting.source_station)
                    if move is not None:
                        waiting.ready_at = max(float(waiting.ready_at), float(move.end_time))
                        break
                    continue
                ok = commit_scheduled_transport(
                    scheduled=scheduled,
                    event_time=current_time,
                    delayed_by_queue=True
                )
                if ok:
                    # commit_scheduled_transport owns lifecycle cleanup and
                    # may already remove this hanger from deferred_transports.
                    # pop(..., None) keeps wake-up idempotent under nested
                    # TRANSPORT_END / QUEUE_RELEASE callbacks.
                    deferred_transports.pop(hanger_id, None)
        for hanger in hangers:
            self.engine.schedule(Event(hanger.entered_station_at, EventType.HANGER_ENTRY, None, hanger.id, None, route[0]))
            state.hanger_route_index[hanger.id] = 0
        event_count_limit = max(1000, int(getattr(self.config, 'event_driven_max_events', 1000000)))
        configured_time_limit = getattr(self.config, 'event_driven_max_time', None)
        if configured_time_limit is None:
            feed = float(getattr(self.config, 'feed_duration', 3600.0))
            warmup = float(getattr(self.config, 'warmup_time', 0.0))
            window = float(getattr(self.config, 'steady_state_window', 600.0))
            configured_time_limit = max(86400.0, feed * 3.0, feed + warmup + 4.0 * window)
        event_time_limit = float(configured_time_limit)
        while self.engine.has_events():
            event = self.engine.pop()
            if len(result.events) >= event_count_limit or float(event.time) > event_time_limit:
                result.deadlocks.append({'type': 'EVENT_DRIVEN_WATCHDOG', 'time': float(event.time), 'event_count': len(result.events), 'time_limit': event_time_limit, 'event_limit': event_count_limit})
                result.event_watchdog_triggered = True
                break
            processor.process(event)
            result.events.append(event)
            if self.progress_callback is not None:
                progress_percent = min(99, max(0, int(
                    float(event.time) / event_time_limit * 100.0
                )))
                if progress_percent != self._last_progress_percent:
                    self._last_progress_percent = progress_percent
                    self.progress_callback(
                        progress_percent,
                        float(event.time),
                        event_time_limit,
                        len(result.events)
                    )
            if event.event_type == EventType.HANGER_ENTRY:
                if event.hanger_id not in state.hanger_requested_entry_time:
                    state.hanger_requested_entry_time[event.hanger_id] = event.time
                if not station_manager.is_available(event.target_station, event.time):
                    entry_queue.enqueue(event.hanger_id)
                    continue
                station = station_map[event.target_station]
                process_time = process_engine.process_time(station)
                result.total_process_time += process_time
                station_manager.occupy(station_id=event.target_station, hanger_id=event.hanger_id, occupied_until=event.time + process_time)
                if event.hanger_id not in state.hanger_actual_entry_time:
                    state.hanger_actual_entry_time[event.hanger_id] = event.time
                state.station_entry_times[event.hanger_id, event.target_station] = event.time
                predictive_pickup.schedule_check(hanger_id=event.hanger_id, station_id=event.target_station, entry_time=event.time)
                self.engine.schedule(Event(event.time + process_time, EventType.PROCESS_END, None, event.hanger_id, event.target_station, event.target_station))
                continue
            if event.event_type == EventType.PREDICTIVE_PICKUP_CHECK:
                source_station = event.target_station
                key = (event.hanger_id, source_station)
                if key in predictive_scheduled_pickups:
                    continue
                if not predictive_pickup.station_still_contains_hanger(station_manager=station_manager, hanger_id=event.hanger_id, station_id=source_station):
                    debug_print(lambda: f'PREDICTIVE_PICKUP_SKIP H={event.hanger_id} S={source_station} reason=HANGER_NOT_ON_STATION')
                    continue
                next_station = predictive_pickup.next_station_for(hanger_id=event.hanger_id, station_id=source_station)
                if next_station is None:
                    continue
                entry_time = state.station_entry_times.get((event.hanger_id, source_station))
                if entry_time is None:
                    continue
                earliest_pickup_time = predictive_pickup.ready_time(source_station, entry_time)
                latest_pickup_time = predictive_pickup.latest_pickup_time(source_station, entry_time)
                commit_horizon = predictive_pickup.commit_horizon_for_station(source_station)
                time_until_ready = earliest_pickup_time - event.time
                if commit_horizon > 0 and time_until_ready > commit_horizon:
                    next_check_time = earliest_pickup_time - commit_horizon
                    if next_check_time <= event.time:
                        next_check_time = event.time
                    self.engine.schedule(Event(next_check_time, EventType.PREDICTIVE_PICKUP_CHECK, None, event.hanger_id, source_station, source_station))
                    debug_print(lambda: f'PREDICTIVE_PICKUP_DEFER_COMMIT H={event.hanger_id} S={source_station} check={event.time:.1f} ready={earliest_pickup_time:.1f} next_check={next_check_time:.1f} horizon={commit_horizon:.1f}')
                    continue
                next_station, schedule_time = self._select_shared_bath_target(next_station, shared_bath_selector, event.time)
                schedule_time = max(float(schedule_time), float(event.time))
                if next_station is None:
                    retry_time = max(float(schedule_time), float(event.time) + self.RETRY_INTERVAL)
                    self.engine.schedule(Event(retry_time, EventType.PREDICTIVE_PICKUP_CHECK, None, event.hanger_id, source_station, source_station))
                    debug_print(lambda: f'SHARED_BATH_PREDICTIVE_RETRY H={event.hanger_id} S={source_station} current={event.time:.1f} retry_at={retry_time:.1f} reason=GROUP_OCCUPIED')
                    continue
                debug_print(lambda: f'PREDICTIVE_PICKUP H={event.hanger_id} {source_station}->{next_station} check={event.time:.1f} ready={earliest_pickup_time:.1f} latest={latest_pickup_time:.1f}')
                blocker = earlier_deadline_waiting_for_target(event.hanger_id, next_station, latest_pickup_time)
                if blocker is not None:
                    blocker_latest, blocker_hanger, blocker_waiting = blocker
                    defer_transport(hanger_id=event.hanger_id, manipulator_id=None, source_station=source_station, target_station=next_station, current_time=event.time, reason='EARLIER_DEADLINE_SAME_TARGET', ready_at=earliest_pickup_time)
                    debug_print(lambda: f'PREDICTIVE_ADMISSION_BLOCKED H={event.hanger_id} DST={next_station} BY=H{blocker_hanger} blocker_latest={blocker_latest:.1f} own_latest={latest_pickup_time:.1f} wake_by_resource=true')
                    continue
                availability = services.transport_scheduler.assignment_selector.availability
                availability_before = dict(getattr(availability, '_busy_until', {}))
                scheduled = services.transport_scheduler.schedule(hanger_id=event.hanger_id, source_station=source_station, target_station=next_station, current_time=event.time, latest_pickup_time=latest_pickup_time, earliest_pickup_time=earliest_pickup_time, earliest_transport_finish_time=schedule_time)
                if scheduled is None:
                    move = commit_selector_yield(event.time, source_station)
                    retry_time = (
                        float(move.end_time) if move is not None
                        else max(float(event.time) + self.RETRY_INTERVAL, float(earliest_pickup_time))
                    )
                    defer_transport(
                        hanger_id=event.hanger_id,
                        manipulator_id=None,
                        source_station=source_station,
                        target_station=next_station,
                        current_time=event.time,
                        reason='YIELD_REQUIRED' if move is not None else 'PREDICTIVE_BLOCKED',
                        ready_at=retry_time
                    )
                    self.engine.schedule(Event(retry_time, EventType.QUEUE_RELEASE, None, None, None, source_station))
                    debug_print(lambda: f'PREDICTIVE_PICKUP_FAILED H={event.hanger_id} SRC={source_station} DST={next_station} T={event.time:.1f}')
                    continue
                state.pending_process_end_times[event.hanger_id, source_station] = earliest_pickup_time
                ok = commit_scheduled_transport(scheduled=scheduled, event_time=event.time)
                if ok:
                    predictive_scheduled_pickups.add(key)
                else:
                    # AssignmentSelector reserves the chosen manipulator while
                    # building the candidate. A failed final track validation
                    # must roll back that speculative reservation. Keep YIELD
                    # reservations for their own manipulators, but do not make
                    # the blocked pickup reserve its manipulator twice.
                    manipulator_id = int(scheduled.manipulator_id)
                    previous_busy = availability_before.get(manipulator_id)
                    if previous_busy is None:
                        getattr(availability, '_busy_until', {}).pop(
                            manipulator_id, None
                        )
                    else:
                        availability.reserve(manipulator_id, previous_busy)
                continue
            if event.event_type == EventType.PROCESS_END:
                state.pending_process_end_times[event.hanger_id, event.target_station] = event.time
                current_index = state.hanger_route_index[event.hanger_id]
                next_index = current_index + 1
                predictive_key = (event.hanger_id, event.target_station)
                if (
                    predictive_key in active_transport_keys
                    or predictive_key in completed_transport_keys
                    or event.hanger_id in deferred_transports
                ):
                    debug_print(lambda: f'PROCESS_END_SKIP_TRANSPORT_PENDING H={event.hanger_id} S={event.target_station} T={event.time:.1f}')
                    continue
                if predictive_key in predictive_scheduled_pickups:
                    debug_print(lambda: f'PROCESS_END_SKIP_ALREADY_PREDICTED H={event.hanger_id} S={event.target_station} T={event.time:.1f}')
                    continue
                if next_index >= len(route):
                    services.transport_scheduler.release_source_station_at_pickup(hanger_id=event.hanger_id, source_station=event.target_station, pickup_time=event.time)
                    station_manager.release(event.target_station)
                    self.engine.schedule(Event(event.time, EventType.HANGER_EXIT, None, event.hanger_id, event.target_station, None))
                    self.engine.schedule(Event(event.time, EventType.QUEUE_RELEASE, None, None, None, event.target_station))
                    wake_deferred_transports(current_time=event.time, reason='PROCESS_END_EXIT_RELEASE')
                    continue
                next_station = route[next_index]
                next_station, schedule_time = self._select_shared_bath_target(next_station, shared_bath_selector, event.time)
                if next_station is None:
                    schedule_shared_bath_retry(event=event, retry_time=schedule_time, reason='GROUP_OCCUPIED')
                    continue
                deadline_text = deadline_transport.describe(hanger_id=event.hanger_id, station_id=event.target_station, current_time=event.time)
                debug_print(lambda: f'H={event.hanger_id} {event.target_station} -> {next_station} schedule_at={schedule_time:.1f} {deadline_text}')
                latest_pickup_time = deadline_transport.latest_pickup_time(hanger_id=event.hanger_id, station_id=event.target_station)
                scheduled = services.transport_scheduler.schedule(hanger_id=event.hanger_id, source_station=event.target_station, target_station=next_station, current_time=event.time, latest_pickup_time=latest_pickup_time, earliest_transport_finish_time=schedule_time)
                if scheduled is None:
                    debug_print(lambda: f'SCHEDULE FAILED H={event.hanger_id} SRC={event.target_station} DST={next_station} T={event.time:.1f} SCHEDULE_AT={schedule_time:.1f}')
                    defer_transport(hanger_id=event.hanger_id, manipulator_id=None, source_station=event.target_station, target_station=next_station, current_time=event.time, reason='ASSIGNMENT_BLOCKED')
                    continue
                ok = commit_scheduled_transport(scheduled=scheduled, event_time=event.time)
                if not ok:
                    continue
                continue
            if event.event_type == EventType.TRANSPORT_END:
                transport_key = (int(event.hanger_id), int(event.source_station))
                if transport_key not in active_transport_keys:
                    debug_print(lambda: f'DUPLICATE_TRANSPORT_END_SKIPPED H={event.hanger_id} S={event.source_station}')
                    continue
                active_transport_keys.remove(transport_key)
                completed_transport_keys.add(transport_key)
                deferred_transports.pop(int(event.hanger_id), None)
                target_station = event.target_station
                if not station_manager.is_available(target_station, event.time):
                    queue_manager.enqueue(target_station, WaitingTransport(hanger_id=event.hanger_id, manipulator_id=event.manipulator_id, source_station=event.source_station, target_station=target_station, requested_at=event.time, ready_at=event.time, process_time=0))
                    continue
                if event.source_station is not None:
                    station_manager.release(event.source_station)
                    if event.source_station == route[0]:
                        self.engine.schedule(Event(event.time, EventType.ENTRY_RELEASE, None, None, None, route[0]))
                    self.engine.schedule(Event(event.time, EventType.QUEUE_RELEASE, None, None, None, event.source_station))
                current_index = state.hanger_route_index[event.hanger_id]
                state.hanger_route_index[event.hanger_id] = current_index + 1
                station = station_map[target_station]
                process_time = process_engine.process_time(station)
                result.total_process_time += process_time
                station_manager.occupy(station_id=target_station, hanger_id=event.hanger_id, occupied_until=event.time + process_time)
                state.station_entry_times[event.hanger_id, target_station] = event.time
                predictive_pickup.schedule_check(hanger_id=event.hanger_id, station_id=target_station, entry_time=event.time)
                self.engine.schedule(Event(event.time + process_time, EventType.PROCESS_END, None, event.hanger_id, target_station, target_station))
                wake_deferred_transports(current_time=event.time, reason='TRANSPORT_END')
                continue
            if event.event_type == EventType.RETRY_TRANSPORT:
                continue
            if event.event_type == EventType.ENTRY_RELEASE:
                if entry_queue.empty():
                    wake_deferred_transports(current_time=event.time, reason='ENTRY_RELEASE_EMPTY')
                    continue
                hanger_id = entry_queue.dequeue()
                self.engine.schedule(Event(event.time, EventType.HANGER_ENTRY, None, hanger_id, None, route[0]))
                wake_deferred_transports(current_time=event.time, reason='ENTRY_RELEASE')
                continue
            if event.event_type == EventType.QUEUE_RELEASE:
                waiting = queue_manager.dequeue(event.target_station)
                if waiting is None:
                    wake_deferred_transports(current_time=event.time, reason='QUEUE_RELEASE_EMPTY')
                    continue
                info = deadlock_detector.detect(current_time=event.time, station_id=event.target_station, transport=waiting)
                if info is not None:
                    if not hasattr(result, 'queue_delays'):
                        result.queue_delays = []
                    result.queue_delays.append(info)
                self.engine.schedule(Event(event.time, EventType.TRANSPORT_END, waiting.manipulator_id, waiting.hanger_id, waiting.source_station, waiting.target_station))
                wake_deferred_transports(current_time=event.time, reason='QUEUE_RELEASE')
                continue
        if deferred_transports:
            debug_print(lambda: '')
            debug_print(lambda: '=' * 60)
            debug_print(lambda: 'SIMULATION STOPPED WITH DEFERRED TRANSPORTS')
            debug_print(lambda: '=' * 60)
            for waiting in deferred_transports.values():
                debug_print(lambda: f'H={waiting.hanger_id} {waiting.source_station}->{waiting.target_station} requested_at={waiting.requested_at:.1f}')
            debug_print(lambda: '=' * 60)
        result.deferred_transports = list(deferred_transports.values())
        result.final_time = state.current_time
        result.processed_events = state.completed_events
        result.completed_transports = state.completed_transports
        result.scheduled_transports = len(result.manipulator_tasks)
        transport_engine = services.transport_scheduler.assignment_selector.transport_engine
        result.event_track_yields = list(getattr(getattr(transport_engine, 'yield_planner', None), 'moves', []))
        for yield_move in result.event_track_yields:
            last_time, _ = last_manipulator_state[yield_move.yielding_manipulator_id]
            if yield_move.end_time >= last_time:
                last_manipulator_state[yield_move.yielding_manipulator_id] = (yield_move.end_time, yield_move.end_position)
        for manipulator in self.config.manipulators:
            last_time, last_position = last_manipulator_state[manipulator.id]
            if result.final_time > last_time:
                result.timeline_segments.append(ManipulatorTimelineSegment(manipulator_id=manipulator.id, start_time=last_time, end_time=result.final_time, start_position=last_position, end_position=last_position, segment_type='idle'))
        result.timeline_segments = YieldTimelineIntegrator().integrate(result.timeline_segments, result.event_track_yields)
        result.station_entry_times = dict(state.station_entry_times)
        result.hanger_requested_entry_time = state.hanger_requested_entry_time
        result.hanger_actual_entry_time = state.hanger_actual_entry_time
        self._finalize_steady_state(result)
        from src.analysis.theoretical_capacity_analyzer import TheoreticalCapacityAnalyzer
        from src.analysis.theoretical_capacity_report import TheoreticalCapacityTextReport
        steady_capacity = getattr(result, 'steady_state', None) or {}
        achieved_throughput = float(steady_capacity.get('interval_throughput', steady_capacity.get('precise_throughput', 0.0)) or 0.0)
        result.theoretical_capacity = TheoreticalCapacityAnalyzer().analyze(configuration=self.config, route=route, best_simulated_throughput=achieved_throughput)
        result.theoretical_capacity_text = TheoreticalCapacityTextReport().render(result.theoretical_capacity)
        print()
        print(result.theoretical_capacity_text)
        from src.analysis.lead_time_report import LeadTimeReport
        LeadTimeReport().print_summary(result)
        from src.analysis.event_diagnostics import EventDiagnostics
        EventDiagnostics().print_summary(result)
        queue_manager.diagnostics.print_summary()
        from src.analysis.process_compliance_report import ProcessComplianceReport
        ProcessComplianceReport().print_summary(result)
        from src.analysis.manipulator_utilization_report import ManipulatorUtilizationReport
        ManipulatorUtilizationReport().print_summary(result, self.config)
        from src.analysis.station_residence_report import StationResidenceReport
        StationResidenceReport().print_summary(result, self.config)
        from src.analysis.manipulator_separation_report import ManipulatorSeparationReport
        separation_report = ManipulatorSeparationReport()
        separation = separation_report.analyze(result, self.config)
        result.event_track_conflicts_prevented = list(getattr(services.transport_scheduler.assignment_selector.transport_engine, 'prevented_track_conflicts', []))
        result.event_track_safety_violation = bool(separation.status == 'COLLISION' or separation.minimum_distance + 1e-06 < float(getattr(self.config, 'minimum_manipulator_spacing', 0.0)))
        if result.event_track_safety_violation:
            result.deadlocks.append({'type': 'EVENT_TRACK_SAFETY_INVARIANT_BROKEN', 'time': separation.time, 'manipulator_a': separation.manipulator_a, 'manipulator_b': separation.manipulator_b, 'minimum_distance': separation.minimum_distance, 'required_distance': separation.required_spacing})
        separation_report.print_summary(result, self.config)
        station_reservation_service.print_summary()
        retry_executed = int(shared_bath_retry_stats['executed'])
        result.shared_bath_retry_diagnostics = {
            'executed': retry_executed,
            'avoided_intervals': int(
                shared_bath_retry_stats['avoided_intervals']
            ),
            'average_delay': (
                shared_bath_retry_stats['total_delay'] / retry_executed
                if retry_executed else 0.0
            ),
        }
        if self.progress_callback is not None:
            self.progress_callback(
                100, float(result.final_time), event_time_limit, len(result.events)
            )

        return result
