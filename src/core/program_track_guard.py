from src.core.simulation_debug import debug_print
class ProgramTrackGuard:
    """Track safety policy for ProgramDriven execution.

    The service owns mode normalization, conflict reporting, and OFF/WARN/
    ENFORCE decisions. Geometry and timeline mutation stay behind callbacks
    supplied by ProgramDrivenSimulator, which keeps this extraction behavior-
    preserving and independently testable.
    """
    OFF = 'off'
    WARN = 'warn'
    ENFORCE = 'enforce'
    _ALIASES = {'0': OFF, 'false': OFF, 'disabled': OFF, 'none': OFF, 'warning': WARN, 'diagnostic': WARN, 'diagnostics': WARN, 'on': ENFORCE, 'true': ENFORCE, 'block': ENFORCE}

    def __init__(self, configuration, conflict_finder, idle_appender, logical_step_resolver, wait_epsilon=0.1, max_iterations=100):
        self.configuration = configuration
        self.conflict_finder = conflict_finder
        self.idle_appender = idle_appender
        self.logical_step_resolver = logical_step_resolver
        self.wait_epsilon = float(wait_epsilon)
        self.max_iterations = int(max_iterations)

    def mode(self):
        value = str(getattr(self.configuration, 'program_driven_track_guard_mode', self.OFF)).strip().lower()
        value = self._ALIASES.get(value, value)
        if value not in [self.OFF, self.WARN, self.ENFORCE]:
            return self.OFF
        return value

    def record(self, runtime, start_time, end_time, source_position, target_position, conflict, mode, enforced_wait=0.0):
        return {'mode': mode, 'time': float(start_time), 'move_end': float(end_time), 'wait_until': float(start_time) + float(enforced_wait), 'wait_time': float(enforced_wait), 'manipulator_id': int(runtime.manipulator_id), 'plc_index': int(runtime.current_plc_index), 'logical_step_no': self.logical_step_resolver(runtime.current_plc_index), 'source_position': float(source_position), 'target_position': float(target_position), 'other_manipulator_id': int(conflict['other_manipulator_id']), 'other_start_time': float(conflict['other_start_time']), 'other_end_time': float(conflict['other_end_time']), 'other_start_position': float(conflict['other_start_position']), 'other_end_position': float(conflict['other_end_position']), 'distance': float(conflict['distance']), 'minimum_spacing': float(conflict['minimum_spacing']), 'conflict_end_time': float(conflict['conflict_end_time'])}

    def apply(self, result, state, runtime, start_time, end_time, source_position, target_position):
        mode = self.mode()
        travel_duration = float(end_time) - float(start_time)
        if travel_duration <= 0.0 or mode == self.OFF:
            return (start_time, end_time)
        for _iteration in range(self.max_iterations):
            conflict = self.conflict_finder(result=result, runtime=runtime, start_time=start_time, end_time=end_time, source_position=source_position, target_position=target_position)
            if conflict is None:
                return (start_time, end_time)
            if mode == self.WARN:
                record = self.record(runtime, start_time, end_time, source_position, target_position, conflict, mode, 0.0)
                state['track_guard_events'].append(record)
                debug_print(lambda: f"PROGRAM TRACKGUARD WARN M={record['manipulator_id']} INDEX={record['plc_index']} move={record['source_position']:.0f}->{record['target_position']:.0f} time={record['time']:.1f}..{record['move_end']:.1f} conflict_with=M{record['other_manipulator_id']} other_move={record['other_start_position']:.0f}->{record['other_end_position']:.0f} other_time={record['other_start_time']:.1f}..{record['other_end_time']:.1f} distance={record['distance']:.2f} required={record['minimum_spacing']:.2f} action=NOT_BLOCKED")
                return (start_time, end_time)
            wait_start = float(start_time)
            wait_end = max(wait_start, float(conflict['conflict_end_time']) + self.wait_epsilon)
            if wait_end > wait_start:
                enforced_wait = wait_end - wait_start
                self.idle_appender(result=result, runtime=runtime, start_time=wait_start, end_time=wait_end)
                record = self.record(runtime, wait_start, end_time, source_position, target_position, conflict, mode, enforced_wait)
                record['wait_until'] = wait_end
                state['track_waits'].append(record)
                state['track_guard_events'].append(record)
                debug_print(lambda: f"PROGRAM TRACKGUARD ENFORCE M={record['manipulator_id']} INDEX={record['plc_index']} move={record['source_position']:.0f}->{record['target_position']:.0f} wait={record['wait_time']:.1f} blocked_by=M{record['other_manipulator_id']} distance={record['distance']:.2f} required={record['minimum_spacing']:.2f}")
            start_time = wait_end
            end_time = start_time + travel_duration
        raise RuntimeError('ProgramDrivenSimulator track safety guard watchdog exceeded')
