from src.core.simulation_preflight import SimulationPreflightValidator
from src.core.simulation_debug import debug_print
import heapq
from src.core.process_limit_classifier import assess_process_time
from src.model.event import Event
from src.model.event_type import EventType
from src.model.simulation_result import SimulationResult
from src.model.manipulator_task import ManipulatorTask
from src.model.manipulator_timeline_segment import ManipulatorTimelineSegment
from src.model.process_compliance_record import ProcessComplianceRecord
from src.model.program_runtime_state import ProgramRuntimeState
from src.model.program_word_execution import ProgramWordExecution
from src.analysis.steady_state_detector import SteadyStateDetector
from src.analysis.program_cycle_kpi import ProgramCycleKPI
from src.analysis.program_residence_auditor import ProgramResidenceAuditor
from src.core.program_track_guard import ProgramTrackGuard
from src.core.program_track_conflict_detector import ProgramTrackConflictDetector
from src.core.program_consult_synchronizer import ProgramConsultSynchronizer

class ProgramDrivenSimulator:
    ACTION_PICKUP = 1
    ACTION_DROP = 2
    WORD_STATION = 'STATION'
    WORD_ACTION = 'ACTION'
    WORD_WAIT = 'WAIT'
    RECHECK_INTERVAL = 0.1
    TRACK_WAIT_EPSILON = 0.1
    TRACK_DISTANCE_EPSILON = 1e-06
    TRACK_GUARD_OFF = ProgramTrackGuard.OFF
    TRACK_GUARD_WARN = ProgramTrackGuard.WARN
    TRACK_GUARD_ENFORCE = ProgramTrackGuard.ENFORCE
    INITIAL_STATE_CYCLE = 'cycle'
    INITIAL_STATE_EMPTY = 'empty'
    TRANSFER_DROP_STATION = 23
    TRANSFER_PICKUP_STATION = 24

    def __init__(self, configuration, programs, consults=None, cycles=10, initial_station_occupancy=None, initial_manipulator_positions=None, initial_state_mode=None):
        self.configuration = configuration
        self.programs = programs or {}
        self.consults = consults or []
        self.cycles = int(cycles)
        self.initial_state_mode = self._normalize_initial_state_mode(initial_state_mode)
        self.initial_station_occupancy = self._normalize_initial_station_occupancy(initial_station_occupancy)
        self.initial_manipulator_positions = self._normalize_initial_manipulator_positions(initial_manipulator_positions)
        self._event_counter = 0
        self.track_conflict_detector = ProgramTrackConflictDetector(configuration=self.configuration, distance_epsilon=self.TRACK_DISTANCE_EPSILON)
        self.track_guard = ProgramTrackGuard(configuration=self.configuration, conflict_finder=self.track_conflict_detector.find_conflict, idle_appender=self._append_idle_segment, logical_step_resolver=self._logical_step_no_for_index, wait_epsilon=self.TRACK_WAIT_EPSILON)
        self.consult_synchronizer = ProgramConsultSynchronizer(consults=self.consults, completed_target_resolver=self._completed_target_index, target_time_resolver=self._target_index_time, recheck_interval=self.RECHECK_INTERVAL)

    def _normalize_initial_state_mode(self, initial_state_mode):
        if initial_state_mode is None:
            initial_state_mode = getattr(self.configuration, 'program_driven_initial_state_mode', self.INITIAL_STATE_CYCLE)
        value = str(initial_state_mode).strip().lower()
        if value in ['empty', 'empty_line', 'pusta', 'pusta_linia']:
            return self.INITIAL_STATE_EMPTY
        return self.INITIAL_STATE_CYCLE

    def _uses_empty_initial_state(self):
        return self.initial_state_mode == self.INITIAL_STATE_EMPTY

    def _normalize_initial_station_occupancy(self, initial_station_occupancy):
        if not initial_station_occupancy:
            return {}
        result = {}
        for station_id, occupancy in initial_station_occupancy.items():
            try:
                station_id = int(station_id)
                occupancy = int(occupancy)
            except Exception:
                continue
            if occupancy <= 0:
                continue
            result[station_id] = occupancy
        return result

    def _normalize_initial_manipulator_positions(self, initial_manipulator_positions):
        if not initial_manipulator_positions:
            return {}
        result = {}
        for manipulator_id, position in initial_manipulator_positions.items():
            try:
                manipulator_id = int(manipulator_id)
                position = int(round(float(position)))
            except Exception:
                continue
            result[manipulator_id] = position
        return result

    def _initial_position_for_manipulator(self, manipulator_id, fallback_position):
        manipulator_id = int(manipulator_id)
        if self._uses_empty_initial_state():
            return fallback_position
        if manipulator_id in self.initial_manipulator_positions:
            return self.initial_manipulator_positions[manipulator_id]
        return fallback_position

    def _as_int_id(self, value):
        try:
            return int(value)
        except Exception:
            return value

    def _route(self):
        route = []
        processed_groups = set()
        for station in getattr(self.configuration, 'stations', []):
            if not getattr(station, 'enabled', True):
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

    def _station_map(self):
        return {station.id: station for station in getattr(self.configuration, 'stations', [])}

    def _manipulator_map(self):
        return {manipulator.id: manipulator for manipulator in getattr(self.configuration, 'manipulators', [])}

    def _program_for_manipulator(self, manipulator_id):
        if manipulator_id in self.programs:
            return self.programs[manipulator_id]
        int_id = self._as_int_id(manipulator_id)
        if int_id in self.programs:
            return self.programs[int_id]
        str_id = str(manipulator_id)
        if str_id in self.programs:
            return self.programs[str_id]
        return None

    def _program_manipulator_ids(self):
        result = []
        for key in self.programs.keys():
            result.append(self._as_int_id(key))
        return sorted(result)

    def _push_runtime(self, queue, runtime):
        self._event_counter += 1
        heapq.heappush(queue, (runtime.available_time, self._event_counter, runtime.manipulator_id))

    def _program_steps(self, manipulator_id):
        program = self._program_for_manipulator(manipulator_id)
        if program is None:
            return []
        steps = []
        for step in getattr(program, 'steps', []):
            try:
                action = int(step.action)
            except Exception:
                continue
            if action in [self.ACTION_PICKUP, self.ACTION_DROP]:
                steps.append(step)
        return steps

    def _is_empty_parking_step(self, step):
        return str(getattr(step, 'segment_type', '')) == 'empty_parking'

    def _max_plc_index(self, manipulator_id):
        return len(self._program_steps(manipulator_id)) * 3

    def _logical_step_no_for_index(self, plc_index):
        return (int(plc_index) - 1) // 3 + 1

    def _word_kind_for_index(self, plc_index):
        mod = (int(plc_index) - 1) % 3
        if mod == 0:
            return self.WORD_STATION
        if mod == 1:
            return self.WORD_ACTION
        return self.WORD_WAIT

    def _step_for_index(self, manipulator_id, plc_index):
        logical_step_no = self._logical_step_no_for_index(plc_index)
        steps = self._program_steps(manipulator_id)
        index = logical_step_no - 1
        if index < 0 or index >= len(steps):
            return None
        return steps[index]

    def _word_address(self, manipulator_id, plc_index):
        program = self._program_for_manipulator(manipulator_id)
        if program is None:
            return 0
        return int(program.index_address) + int(plc_index)

    def _word_value(self, step, word_kind):
        if word_kind == self.WORD_STATION:
            return int(step.plc_station_value)
        if word_kind == self.WORD_ACTION:
            return int(step.action)
        return int(step.wait_time_01s)

    def _travel_time(self, manipulator, source_station, target_station):
        return abs(int(round(target_station)) - int(round(source_station))) * manipulator.travel_time_per_position

    def _new_hanger_id(self, state):
        state['next_hanger_id'] += 1
        return state['next_hanger_id']

    def _initial_line_fill_from_explicit_occupancy(self, state, load_station, unload_station):
        if not self.initial_station_occupancy:
            return False
        station_map = self._station_map()
        prefilled_count = 0
        for station_id, occupancy in sorted(self.initial_station_occupancy.items()):
            if station_id == load_station or station_id == unload_station:
                continue
            if occupancy <= 0:
                continue
            if occupancy > 1:
                debug_print(lambda: f'PROGRAM PREFILL WARNING S={station_id} occupancy={occupancy}. Model stanowiska ma pojemność 1, więc zostanie użyta jedna zawieszka.')
            if station_id in state['station_hangers']:
                continue
            hanger_id = self._new_hanger_id(state)
            state['station_hangers'][station_id] = hanger_id
            station = station_map.get(station_id)
            min_process_time = 0.0
            if station is not None:
                min_process_time = float(getattr(station, 'min_process_time', 0.0))
            entry_time = 0.0 - min_process_time
            state['station_entry_times'][hanger_id, station_id] = entry_time
            prefilled_count += 1
            debug_print(lambda: f'PROGRAM PREFILL FROM CYCLE H={hanger_id} S={station_id} occupancy={occupancy} entry={entry_time:.1f}')
        state['prefilled_hangers'] = prefilled_count
        debug_print(lambda: f'PROGRAM INITIAL LINE FILL FROM CYCLE prefilled={prefilled_count}')
        return True

    def _initial_line_fill(self, result, state, load_station, unload_station):
        if self._uses_empty_initial_state():
            state['prefilled_hangers'] = 0
            debug_print(lambda: 'PROGRAM INITIAL STATE MODE: EMPTY')
            debug_print(lambda: 'PROGRAM INITIAL LINE FILL: skipped')
            debug_print(lambda: 'PROGRAM INITIAL OCCUPANCY: []')
            debug_print(lambda: f'PROGRAM HANGERS MAY ONLY ENTER AT S={load_station}')
            debug_print(lambda: f'PROGRAM HANGERS EXIT AT S={unload_station}')
            return
        debug_print(lambda: 'PROGRAM INITIAL STATE MODE: CYCLE')
        if self._initial_line_fill_from_explicit_occupancy(state=state, load_station=load_station, unload_station=unload_station):
            return
        interactions_by_station = {}
        station_map = self._station_map()
        for manipulator_id in self._program_manipulator_ids():
            program = self._program_for_manipulator(manipulator_id)
            if program is None:
                continue
            for step in getattr(program, 'steps', []):
                if getattr(step, 'segment_type', '') == 'empty_parking':
                    continue
                if step.action not in [self.ACTION_PICKUP, self.ACTION_DROP]:
                    continue
                station_id = int(round(step.station_id))
                if station_id == load_station or station_id == unload_station:
                    continue
                action_name = 'PICKUP' if step.action == self.ACTION_PICKUP else 'DROP'
                interaction_time = float(getattr(step, 'cycle_time_start', 0.0))
                if station_id not in interactions_by_station:
                    interactions_by_station[station_id] = []
                interactions_by_station[station_id].append((interaction_time, manipulator_id, step.step_no, station_id, action_name, step))
        prefilled_count = 0
        for station_id, interactions in sorted(interactions_by_station.items()):
            interactions.sort(key=lambda item: (item[0], item[1], item[2]))
            balance = 0
            min_balance = 0
            first_deficit_interaction = None
            for interaction in interactions:
                action_name = interaction[4]
                if action_name == 'DROP':
                    balance += 1
                elif action_name == 'PICKUP':
                    balance -= 1
                if balance < min_balance:
                    min_balance = balance
                    first_deficit_interaction = interaction
            initial_hangers_needed = -min_balance
            if initial_hangers_needed <= 0:
                continue
            if initial_hangers_needed > 1:
                debug_print(lambda: f'PROGRAM PREFILL WARNING S={station_id} requires={initial_hangers_needed} initial hangers. Station capacity model will prefill only 1.')
            if station_id in state['station_hangers']:
                continue
            hanger_id = self._new_hanger_id(state)
            state['station_hangers'][station_id] = hanger_id
            station = station_map.get(station_id)
            min_process_time = 0.0
            if station is not None:
                min_process_time = float(getattr(station, 'min_process_time', 0.0))
            interaction_time = 0.0
            manipulator_id = None
            step_no = None
            if first_deficit_interaction is not None:
                interaction_time = float(first_deficit_interaction[0])
                manipulator_id = first_deficit_interaction[1]
                step_no = first_deficit_interaction[2]
            entry_time = interaction_time - min_process_time
            state['station_entry_times'][hanger_id, station_id] = entry_time
            prefilled_count += 1
            debug_print(lambda: f'PROGRAM PREFILL H={hanger_id} S={station_id} required_by_balance M={manipulator_id} step={step_no} entry={entry_time:.1f}')
        state['prefilled_hangers'] = prefilled_count
        if prefilled_count > 0:
            debug_print(lambda: f'PROGRAM INITIAL LINE FILL prefilled={prefilled_count}')

    def _add_event(self, result, time_value, event_type, manipulator_id, hanger_id, source_station, target_station):
        result.events.append(Event(time_value, event_type, manipulator_id, hanger_id, source_station, target_station))

    def _track_guard_mode(self):
        return self.track_guard.mode()

    def _track_guard_record(self, runtime, start_time, end_time, source_position, target_position, conflict, mode, enforced_wait=0.0):
        return self.track_guard.record(runtime=runtime, start_time=start_time, end_time=end_time, source_position=source_position, target_position=target_position, conflict=conflict, mode=mode, enforced_wait=enforced_wait)

    def _minimum_track_spacing(self):
        return self.track_conflict_detector.minimum_spacing()

    def _position_on_linear_segment(self, start_time, end_time, start_position, end_position, time_value):
        return self.track_conflict_detector.position_on_segment(start_time, end_time, start_position, end_position, time_value)

    def _minimum_distance_between_linear_segments(self, a_start_time, a_end_time, a_start_position, a_end_position, b_start_time, b_end_time, b_start_position, b_end_position):
        return self.track_conflict_detector.minimum_distance(a_start_time, a_end_time, a_start_position, a_end_position, b_start_time, b_end_time, b_start_position, b_end_position)

    def _track_conflict_for_move(self, result, runtime, start_time, end_time, source_position, target_position):
        return self.track_conflict_detector.find_conflict(result=result, runtime=runtime, start_time=start_time, end_time=end_time, source_position=source_position, target_position=target_position)

    def _apply_track_safety_guard(self, result, state, runtime, start_time, end_time, source_position, target_position):
        return self.track_guard.apply(result=result, state=state, runtime=runtime, start_time=start_time, end_time=end_time, source_position=source_position, target_position=target_position)

    def _record_compliance(self, result, state, hanger_id, station_id, pickup_time):
        station = self._station_map().get(station_id)
        if station is None:
            return
        entry_time = state['station_entry_times'].get((hanger_id, station_id))
        if entry_time is None:
            return
        actual_time = pickup_time - entry_time
        min_time = float(station.min_process_time)
        max_time = float(station.max_process_time)
        assessment = assess_process_time(station, actual_time)
        min_ok = assessment.nominal_min_ok
        max_ok = assessment.nominal_max_ok
        violation_type = assessment.status
        result.process_compliance.append(ProcessComplianceRecord(hanger_id=hanger_id, station_id=station_id, entry_time=entry_time, exit_time=pickup_time, actual_time=actual_time, min_time=min_time, max_time=max_time, min_ok=min_ok, max_ok=max_ok, violation_type=violation_type, possible_min_time=float(station.possible_min_process_time), possible_max_time=float(station.possible_max_process_time), possible_min_ok=assessment.possible_min_ok, possible_max_ok=assessment.possible_max_ok, compliance_status=assessment.status, nominal_deviation=assessment.nominal_deviation))

    def _pickup_release_time(self, state, station_id, pickup_start_time):
        station = self._station_map().get(station_id)
        if station is None or not bool(getattr(station, 'is_process_bath', True)):
            return pickup_start_time
        if station_id not in state['station_hangers']:
            return pickup_start_time
        entry_time = state['station_entry_times'].get(
            (state['station_hangers'][station_id], station_id)
        )
        if entry_time is None:
            return pickup_start_time
        min_process_time = float(getattr(station, 'min_process_time', 0.0) or 0.0)
        return max(pickup_start_time, float(entry_time) + max(0.0, min_process_time))

    def _append_move_segment(self, result, runtime, start_time, end_time, source_position, target_position):
        if end_time <= start_time:
            return
        if int(round(source_position)) == int(round(target_position)):
            return
        if runtime.carrying_hanger_id is None:
            segment_type = 'empty_move'
        else:
            segment_type = 'loaded_move'
        result.timeline_segments.append(ManipulatorTimelineSegment(manipulator_id=runtime.manipulator_id, start_time=start_time, end_time=end_time, start_position=source_position, end_position=target_position, segment_type=segment_type, hanger_id=runtime.carrying_hanger_id, pickup_time=runtime.pickup_finish_time, drop_time=None))

    def _append_idle_segment(self, result, runtime, start_time, end_time):
        if end_time <= start_time:
            return
        result.timeline_segments.append(ManipulatorTimelineSegment(manipulator_id=runtime.manipulator_id, start_time=start_time, end_time=end_time, start_position=runtime.current_position, end_position=runtime.current_position, segment_type='idle', hanger_id=None, pickup_time=None, drop_time=None))

    def _completed_target_index(self, runtimes, target_manipulator_id, target_plc_index):
        runtime = runtimes.get(target_manipulator_id)
        if runtime is None:
            return True
        max_index = self._max_plc_index(target_manipulator_id)
        if target_plc_index > max_index:
            print(f'PROGRAM CONSULT WARNING target index out of range: M{target_manipulator_id} IDX={target_plc_index} max={max_index}. Consult ignored.')
            return True
        return target_plc_index in runtime.completed_indices

    def _target_index_time(self, runtimes, target_manipulator_id, target_plc_index):
        runtime = runtimes.get(target_manipulator_id)
        if runtime is None:
            return None
        max_index = self._max_plc_index(target_manipulator_id)
        if target_plc_index > max_index:
            return runtime.available_time
        return runtime.completed_indices.get(target_plc_index)

    def _blocking_consult(self, runtime, runtimes):
        blocked = self.consult_synchronizer.blocking_consult(runtime, runtimes)
        return None if blocked is None else blocked[1]

    def _pickup_transfer_hanger(self, result, state, runtime, pickup_start_time, pickup_finish_time):
        station_hangers = state['station_hangers']
        hanger_id = station_hangers.pop(self.TRANSFER_DROP_STATION, None)
        if hanger_id is None:
            warning = {'time': pickup_start_time, 'manipulator_id': runtime.manipulator_id, 'station_id': self.TRANSFER_PICKUP_STATION, 'hanger_id': None, 'warmup': self._uses_empty_initial_state(), 'message': 'PICKUP przeładunkowy ST24 bez zawieszki oczekującej na ST23.'}
            state['empty_pickup_warnings'].append(warning)
            print(f'PROGRAM TRANSFER WARNING M={runtime.manipulator_id} T={pickup_start_time:.1f} reason=EMPTY_ST23')
            return None
        runtime.carrying_hanger_id = hanger_id
        runtime.pickup_source_station = self.TRANSFER_DROP_STATION
        runtime.pickup_start_time = pickup_start_time
        runtime.pickup_finish_time = pickup_finish_time
        print(f'PROGRAM TRANSFER PICKUP H={hanger_id} M={runtime.manipulator_id} ST23->ST24 T={pickup_finish_time:.1f}')
        return hanger_id

    def _pickup_hanger(self, result, state, runtime, station_id, pickup_start_time, pickup_finish_time, load_station):
        station_hangers = state['station_hangers']
        if station_id in station_hangers:
            hanger_id = station_hangers.pop(station_id)
        elif station_id == load_station:
            hanger_id = self._new_hanger_id(state)
            state['hanger_requested_entry_time'][hanger_id] = pickup_start_time
            state['hanger_actual_entry_time'][hanger_id] = pickup_start_time
            self._add_event(result, pickup_start_time, EventType.HANGER_ENTRY, None, hanger_id, None, station_id)
        elif self._uses_empty_initial_state():
            warning = {'time': pickup_start_time, 'manipulator_id': runtime.manipulator_id, 'station_id': station_id, 'hanger_id': None, 'warmup': True, 'message': f'PICKUP z pustej stacji S={station_id} podczas rozruchu pustej linii. Nie utworzono syntetycznej zawieszki.'}
            state['empty_pickup_warnings'].append(warning)
            state['warmup_empty_pickups'] += 1
            print(f'PROGRAM WARMUP EMPTY PICKUP M={runtime.manipulator_id} S={station_id} T={pickup_start_time:.1f} synthetic_hanger=False')
            runtime.carrying_hanger_id = None
            runtime.pickup_source_station = None
            runtime.pickup_start_time = None
            runtime.pickup_finish_time = None
            return None
        else:
            hanger_id = self._new_hanger_id(state)
            warning = {'time': pickup_start_time, 'manipulator_id': runtime.manipulator_id, 'station_id': station_id, 'hanger_id': hanger_id, 'warmup': False, 'message': f'PICKUP z pustej stacji S={station_id}. Utworzono syntetyczną zawieszkę H={hanger_id}.'}
            state['empty_pickup_warnings'].append(warning)
            print(f"PROGRAM WARNING M={runtime.manipulator_id} {warning['message']}")
        runtime.carrying_hanger_id = hanger_id
        runtime.pickup_source_station = station_id
        runtime.pickup_start_time = pickup_start_time
        runtime.pickup_finish_time = pickup_finish_time
        self._record_compliance(result=result, state=state, hanger_id=hanger_id, station_id=station_id, pickup_time=pickup_finish_time)
        return hanger_id

    def _drop_hanger(self, result, state, runtime, station_id, drop_finish_time, unload_station):
        hanger_id = runtime.carrying_hanger_id
        if hanger_id is None:
            warning = {'time': drop_finish_time, 'manipulator_id': runtime.manipulator_id, 'station_id': station_id, 'message': f'DROP bez zawieszki na S={station_id}.'}
            state['drop_without_hanger_warnings'].append(warning)
            print(f"PROGRAM WARNING M={runtime.manipulator_id} {warning['message']}")
            return None
        source_station = runtime.pickup_source_station if runtime.pickup_source_station is not None else station_id
        task_start = runtime.pickup_start_time if runtime.pickup_start_time is not None else drop_finish_time
        result.manipulator_tasks.append(ManipulatorTask(manipulator_id=runtime.manipulator_id, hanger_id=hanger_id, source_station=source_station, target_station=station_id, start_time=task_start, end_time=drop_finish_time, wait_time=0.0, shared_bath=False, delayed_by_queue=False, delayed_by_no_passing=False))
        self._add_event(result, drop_finish_time, EventType.TRANSPORT_END, runtime.manipulator_id, hanger_id, source_station, station_id)
        if station_id == unload_station:
            self._add_event(result, drop_finish_time, EventType.HANGER_EXIT, runtime.manipulator_id, hanger_id, station_id, None)
        else:
            if station_id in state['station_hangers']:
                existing_hanger_id = state['station_hangers'][station_id]
                warning = {'time': drop_finish_time, 'manipulator_id': runtime.manipulator_id, 'station_id': station_id, 'hanger_id': hanger_id, 'existing_hanger_id': existing_hanger_id, 'message': f'DROP na zajętą stację S={station_id}. Poprzednia zawieszka H={existing_hanger_id} zostaje nadpisana przez H={hanger_id}.'}
                state['occupied_drop_warnings'].append(warning)
                print(f"PROGRAM WARNING M={runtime.manipulator_id} {warning['message']}")
            state['station_hangers'][station_id] = hanger_id
            state['station_entry_times'][hanger_id, station_id] = drop_finish_time
        runtime.carrying_hanger_id = None
        runtime.pickup_source_station = None
        runtime.pickup_start_time = None
        runtime.pickup_finish_time = None
        return hanger_id

    def _execute_station_word(self, result, state, runtime, manipulator, step, start_time):
        target_station = int(round(step.station_id))
        source_station = int(round(runtime.current_position))
        travel_time = self._travel_time(manipulator, source_station, target_station)
        end_time = start_time + travel_time
        start_time, end_time = self._apply_track_safety_guard(result=result, state=state, runtime=runtime, start_time=start_time, end_time=end_time, source_position=source_station, target_position=target_station)
        self._append_move_segment(result, runtime, start_time, end_time, source_station, target_station)
        runtime.current_position = target_station
        return (end_time, None)

    def _execute_action_word(self, result, state, runtime, manipulator, step, start_time, load_station, unload_station):
        action = int(step.action)
        end_time = start_time
        hanger_id = runtime.carrying_hanger_id
        if self._is_empty_parking_step(step):
            return (end_time, hanger_id)
        if action != runtime.current_action:
            if action == self.ACTION_PICKUP:
                if str(getattr(step, 'status', '')) != 'TRANSFER_24_PICKUP':
                    release_time = self._pickup_release_time(
                        state,
                        runtime.current_position,
                        start_time
                    )
                    if release_time > start_time:
                        self._append_idle_segment(
                            result,
                            runtime,
                            start_time,
                            release_time
                        )
                        debug_print(
                            lambda: (
                                f'PROGRAM BATH PICKUP BLOCKED M={runtime.manipulator_id} '
                                f'S={runtime.current_position} T={start_time:.1f} '
                                f'release_at={release_time:.1f}'
                            )
                        )
                        start_time = release_time
                end_time = start_time + manipulator.lift_time
                if str(getattr(step, 'status', '')) == 'TRANSFER_24_PICKUP':
                    hanger_id = self._pickup_transfer_hanger(result=result, state=state, runtime=runtime, pickup_start_time=start_time, pickup_finish_time=end_time)
                else:
                    hanger_id = self._pickup_hanger(result=result, state=state, runtime=runtime, station_id=runtime.current_position, pickup_start_time=start_time, pickup_finish_time=end_time, load_station=load_station)
            elif action == self.ACTION_DROP:
                end_time = start_time + manipulator.drop_time
                hanger_id = self._drop_hanger(result=result, state=state, runtime=runtime, station_id=runtime.current_position, drop_finish_time=end_time, unload_station=unload_station)
            runtime.current_action = action
        return (end_time, hanger_id)

    def _execute_wait_word(self, result, runtime, step, start_time):
        wait_time = float(step.wait_time_01s) / 10.0
        end_time = start_time + wait_time
        self._append_idle_segment(result, runtime, start_time, end_time)
        return (end_time, runtime.carrying_hanger_id)

    def _apply_schedule_anchor(self, result, runtime, manipulator, step, word_kind):
        if not bool(getattr(self.configuration, 'program_driven_use_schedule_anchors', False)):
            return
        if step is None:
            return
        planned_time = getattr(step, 'cycle_time_start', None)
        if planned_time is None:
            return
        planned_absolute_time = float(getattr(runtime, 'cycle_start_time', 0.0)) + float(planned_time)
        if word_kind == self.WORD_STATION:
            source_station = int(round(runtime.current_position))
            target_station = int(round(step.station_id))
            desired_start_time = planned_absolute_time - self._travel_time(manipulator, source_station, target_station)
        elif word_kind == self.WORD_ACTION:
            desired_start_time = planned_absolute_time
        else:
            return
        if desired_start_time > runtime.available_time:
            self._append_idle_segment(result=result, runtime=runtime, start_time=runtime.available_time, end_time=desired_start_time)
            runtime.available_time = desired_start_time

    def _execute_word(self, result, state, runtime, manipulator, load_station, unload_station):
        plc_index = runtime.current_plc_index
        step = self._step_for_index(runtime.manipulator_id, plc_index)
        if step is None:
            runtime.current_plc_index += 1
            return
        word_kind = self._word_kind_for_index(plc_index)
        word_value = self._word_value(step, word_kind)
        self._apply_schedule_anchor(result=result, runtime=runtime, manipulator=manipulator, step=step, word_kind=word_kind)
        start_time = runtime.available_time
        start_position = runtime.current_position
        hanger_id = runtime.carrying_hanger_id
        if word_kind == self.WORD_STATION:
            end_time, hanger_id = self._execute_station_word(result=result, state=state, runtime=runtime, manipulator=manipulator, step=step, start_time=start_time)
        elif word_kind == self.WORD_ACTION:
            end_time, hanger_id = self._execute_action_word(result=result, state=state, runtime=runtime, manipulator=manipulator, step=step, start_time=start_time, load_station=load_station, unload_station=unload_station)
        else:
            end_time, hanger_id = self._execute_wait_word(result=result, runtime=runtime, step=step, start_time=start_time)
        runtime.completed_indices[plc_index] = end_time
        state['word_executions'].append(ProgramWordExecution(manipulator_id=runtime.manipulator_id, cycle_no=runtime.cycle_no, plc_index=plc_index, word_address=self._word_address(runtime.manipulator_id, plc_index), logical_step_no=step.step_no, word_kind=word_kind, word_value=word_value, start_time=start_time, end_time=end_time, start_position=start_position, end_position=runtime.current_position, action=runtime.current_action, hanger_id=hanger_id, blocked_by_consult=False, status='OK'))
        runtime.available_time = end_time
        runtime.current_plc_index += 1

    def _release_barrier_if_ready(self, queue, runtimes, state):
        active = [runtime for runtime in runtimes.values()]
        if not active:
            return
        if not all((runtime.finished_cycle for runtime in active)):
            return
        release_time = max((runtime.available_time for runtime in active))
        for runtime in active:
            runtime.finished_cycle = False
            runtime.cycle_no += 1
            runtime.current_plc_index = 1
            runtime.completed_indices = {}
            runtime.available_time = release_time
            runtime.cycle_start_time = release_time
            if runtime.cycle_no <= self.cycles:
                self._push_runtime(queue, runtime)

    def _calculate_program_cycle_throughput(self, result):
        """Compatibility wrapper for tests and existing integrations."""
        audit = ProgramCycleKPI().calculate(result)
        if audit is not None:
            print(f"PROGRAM CYCLE THROUGHPUT cycles={audit['complete_cycles']} cycle_time={audit['cycle_duration']:.1f}s hangers_per_cycle={audit['hangers_per_cycle']:.3f} exits={audit['total_unique_exits']} duration={audit['total_cycle_duration']:.1f}s throughput={audit['throughput']:.3f}/h")
        return audit

    def _finalize_steady_state(self, result):
        detector = SteadyStateDetector()
        result.steady_state = detector.detect(result=result, window_size=getattr(self.configuration, 'steady_state_window', 600.0), analysis_start=getattr(self.configuration, 'warmup_time', 0.0), analysis_end=result.final_time)
        result.throughput_windows = result.steady_state.get('windows', []) if result.steady_state is not None else []
        result.program_cycle_kpi = self._calculate_program_cycle_throughput(result)
        if result.program_cycle_kpi is None:
            return
        ProgramCycleKPI().update_steady_state(result, result.program_cycle_kpi)

    def run(self):
        SimulationPreflightValidator().validate(
            self.configuration, self.initial_manipulator_positions
        )
        result = SimulationResult()
        route = self._route()
        if not route:
            return result
        load_station = route[0]
        unload_station = route[-1]
        manipulator_map = self._manipulator_map()
        state = {'next_hanger_id': 0, 'station_hangers': {}, 'station_entry_times': {}, 'hanger_requested_entry_time': {}, 'hanger_actual_entry_time': {}, 'word_executions': [], 'prefilled_hangers': 0, 'warmup_empty_pickups': 0, 'empty_pickup_warnings': [], 'drop_without_hanger_warnings': [], 'occupied_drop_warnings': [], 'track_waits': [], 'track_guard_events': [], 'consult_waits': [], 'active_consult_waits': {}}
        self._initial_line_fill(result=result, state=state, load_station=load_station, unload_station=unload_station)
        runtimes = {}
        queue = []
        for manipulator_id in self._program_manipulator_ids():
            manipulator = manipulator_map.get(manipulator_id)
            if manipulator is None:
                print(f'PROGRAM RUNTIME SKIP M={manipulator_id} reason=MANIPULATOR_NOT_FOUND available={list(manipulator_map.keys())}')
                continue
            max_index = self._max_plc_index(manipulator_id)
            if max_index <= 0:
                print(f'PROGRAM RUNTIME SKIP M={manipulator_id} reason=EMPTY_PROGRAM')
                continue
            initial_position = self._initial_position_for_manipulator(manipulator_id=manipulator_id, fallback_position=manipulator.position)
            runtime = ProgramRuntimeState(manipulator_id=manipulator_id, current_plc_index=1, current_position=initial_position, current_action=self.ACTION_DROP, available_time=0.0, cycle_no=1, cycle_start_time=0.0, finished_cycle=False)
            runtimes[manipulator_id] = runtime
            self._push_runtime(queue, runtime)
        if not runtimes:
            print('PROGRAM RUNTIME INIT FAILED: no manipulator runtimes created.')
            print(f'program_keys={list(self.programs.keys())}')
            print(f'manipulator_keys={list(manipulator_map.keys())}')
            return result
        loop_counter = 0
        while queue:
            loop_counter += 1
            if loop_counter > 500000:
                raise RuntimeError('ProgramDrivenSimulator watchdog exceeded')
            _, _, manipulator_id = heapq.heappop(queue)
            runtime = runtimes[manipulator_id]
            if runtime.cycle_no > self.cycles:
                continue
            if runtime.finished_cycle:
                continue
            max_index = self._max_plc_index(manipulator_id)
            if runtime.current_plc_index > max_index:
                runtime.finished_cycle = True
                self._release_barrier_if_ready(queue, runtimes, state)
                continue
            consult = self.consult_synchronizer.evaluate(state, runtime, runtimes)
            if consult is not None:
                self._push_runtime(queue, runtime)
                continue
            manipulator = manipulator_map[manipulator_id]
            self._execute_word(result=result, state=state, runtime=runtime, manipulator=manipulator, load_station=load_station, unload_station=unload_station)
            self._push_runtime(queue, runtime)
        result.final_time = max([runtime.available_time for runtime in runtimes.values()] or [0.0])
        for runtime in runtimes.values():
            last_execution = max(
                (
                    execution
                    for execution in state['word_executions']
                    if execution.manipulator_id == runtime.manipulator_id
                ),
                key=lambda execution: execution.end_time,
                default=None
            )
            if last_execution is not None and last_execution.end_time < result.final_time:
                result.timeline_segments.append(
                    ManipulatorTimelineSegment(
                        manipulator_id=runtime.manipulator_id,
                        start_time=last_execution.end_time,
                        end_time=result.final_time,
                        start_position=last_execution.end_position,
                        end_position=last_execution.end_position,
                        segment_type='stationary_hold'
                    )
                )
        result.generated_hangers = state['next_hanger_id']
        result.prefilled_hangers = state['prefilled_hangers']
        result.completed_transports = len(result.manipulator_tasks)
        result.scheduled_transports = len(result.manipulator_tasks)
        result.processed_events = len(result.events)
        result.station_entry_times = dict(state['station_entry_times'])
        result.hanger_requested_entry_time = state['hanger_requested_entry_time']
        result.hanger_actual_entry_time = state['hanger_actual_entry_time']
        self.consult_synchronizer.finalize(state, result.final_time)
        result.consult_waits = list(state['consult_waits'])
        print(f'PROGRAM CONSULT WAITS: {len(result.consult_waits)}')
        result.program_word_executions = state['word_executions']
        result.empty_pickup_warnings = state['empty_pickup_warnings']
        result.drop_without_hanger_warnings = state['drop_without_hanger_warnings']
        result.occupied_drop_warnings = state['occupied_drop_warnings']
        result.track_waits = state['track_waits']
        result.track_guard_mode = self._track_guard_mode()
        result.track_guard_events = list(state['track_guard_events'])
        print(f'PROGRAM TRACKGUARD MODE: {result.track_guard_mode.upper()}')
        print(f'PROGRAM TRACKGUARD EVENTS: {len(result.track_guard_events)}')
        result.program_initial_state_mode = self.initial_state_mode
        result.warmup_empty_pickups = state['warmup_empty_pickups']
        print(f'PROGRAM INITIAL STATE: {self.initial_state_mode.upper()}')
        print(f"PROGRAM PREFILLED HANGERS: {state['prefilled_hangers']}")
        print(f"PROGRAM WARMUP EMPTY PICKUPS: {state['warmup_empty_pickups']}")
        exit_events = [event for event in result.events if event.event_type == EventType.HANGER_EXIT]
        configured_station_ids = set(self._station_map().keys())
        technical_compliance = [record for record in result.process_compliance if record.station_id not in configured_station_ids]
        ProgramResidenceAuditor().audit(result=result, configuration=self.configuration, strict=True)
        result.program_driven_kpi_audit = {'hanger_exit_count': len(exit_events), 'unique_exited_hangers': len(set((event.hanger_id for event in exit_events))), 'process_compliance_count': len(result.process_compliance), 'technical_station_compliance_count': len(technical_compliance), 'residence_basis': 'DROP_FINISH_TO_PICKUP_FINISH', 'drip_excluded_from_residence': True, 'residence_audit_valid': result.program_residence_audit['valid'], 'residence_audit_errors': list(result.program_residence_audit['errors'])}
        print(f"PROGRAM KPI AUDIT exits={len(exit_events)} unique_exits={result.program_driven_kpi_audit['unique_exited_hangers']} compliance={len(result.process_compliance)} technical_compliance={len(technical_compliance)} residence=DROP_FINISH_TO_PICKUP_FINISH drip_in_residence=False")
        self._finalize_steady_state(result)
        return result
