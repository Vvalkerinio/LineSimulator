from src.core.simulation_debug import debug_print
import math

class SharedBathSelector:
    ALTERNATE_RETRY_INTERVAL = 30.0

    def __init__(self, station_manager, station_reservation_service=None):
        self.station_manager = station_manager
        self.station_reservation_service = station_reservation_service
        self.last_recommended_time = 0.0
        self.last_selected_station_by_group = {}

    def _finite_or_none(self, value):
        try:
            value = float(value)
        except Exception:
            return None
        if not math.isfinite(value):
            return None
        return value

    def _safe_time(self, value, fallback=0.0):
        value = self._finite_or_none(value)
        if value is None:
            return float(fallback)
        return value

    def _station(self, station_id):
        try:
            return self.station_manager.station(station_id)
        except Exception:
            return None

    def _state(self, station_id):
        try:
            return self.station_manager.state(station_id)
        except Exception:
            return None

    def _normalize_group_name(self, raw_group):
        if raw_group is None:
            return ''
        group = str(raw_group).strip()
        if group == '' or group.lower() == 'none':
            return ''
        return group

    def _group_name_for_station_ids(self, station_ids):
        for station_id in station_ids:
            station = self._station(station_id)
            if station is None:
                continue
            group = self._normalize_group_name(getattr(station, 'shared_bath_group', None))
            if group:
                return group
        return ''

    def _group_key(self, station_ids):
        group_name = self._group_name_for_station_ids(station_ids)
        if group_name:
            return group_name
        return ','.join((str(int(station_id)) for station_id in sorted(station_ids)))

    def _station_min_process_time(self, station_id):
        station = self._station(station_id)
        if station is None:
            return 0.0
        value = self._finite_or_none(getattr(station, 'min_process_time', 0.0))
        if value is None:
            return 0.0
        return max(0.0, value)

    def _station_max_process_time(self, station_id):
        station = self._station(station_id)
        if station is None:
            return 0.0
        value = self._finite_or_none(getattr(station, 'max_process_time', 0.0))
        if value is None:
            return 0.0
        return max(0.0, value)

    def _group_min_process_time(self, station_ids):
        values = []
        for station_id in station_ids:
            value = self._station_min_process_time(station_id)
            if value > 0.0:
                values.append(value)
        if not values:
            return 0.0
        return min(values)

    def _default_percent_for_group(self, station_ids):
        if not station_ids:
            return 0.0
        return 100.0 / max(1, len(station_ids))

    def _normalize_stagger_mode(self, mode):
        mode = str(mode).strip().lower()
        if mode in ['seconds', 'sekundy', 's', 'sec']:
            return 'seconds'
        if mode in ['alternate', 'alternating', 'naprzemiennie', 'raz_jedna_raz_druga']:
            return 'alternate'
        return 'percent'

    def _stagger_rule_for_group(self, station_ids):
        group_name = self._group_name_for_station_ids(station_ids)
        for station_id in station_ids:
            station = self._station(station_id)
            if station is None:
                continue
            mode = getattr(station, 'shared_bath_stagger_mode', None)
            value = getattr(station, 'shared_bath_stagger_value', None)
            if mode is not None and value is not None:
                value = self._finite_or_none(value)
                if value is None:
                    value = 0.0
                return (group_name, self._normalize_stagger_mode(mode), value)
        return (group_name, 'percent', self._default_percent_for_group(station_ids))

    def _target_gap(self, station_ids):
        if not station_ids:
            return 0.0
        _group_name, mode, value = self._stagger_rule_for_group(station_ids)
        if mode == 'alternate':
            return 0.0
        group_min_time = self._group_min_process_time(station_ids)
        if group_min_time <= 0.0:
            return 0.0
        value = max(0.0, float(value))
        if mode == 'seconds':
            return value
        return group_min_time * value / 100.0

    def _state_is_occupied(self, state):
        if state is None:
            return False
        for attribute_name in ['hanger_id', 'current_hanger_id', 'occupied_hanger_id']:
            if getattr(state, attribute_name, None) is not None:
                return True
        if bool(getattr(state, 'occupied', False)):
            return True
        return False

    def _state_entry_time(self, state):
        if state is None:
            return None
        for attribute_name in ['entry_time', 'occupied_from', 'occupied_since', 'start_time', 'last_fill_time']:
            value = self._finite_or_none(getattr(state, attribute_name, None))
            if value is not None:
                return value
        return None

    def _state_occupied_until(self, state):
        if state is None:
            return None
        for attribute_name in ['occupied_until', 'release_time', 'reserved_until', 'end_time']:
            value = self._finite_or_none(getattr(state, attribute_name, None))
            if value is not None:
                return value
        return None

    def _station_is_available(self, station_id, current_time):
        current_time = self._safe_time(current_time, 0.0)
        try:
            return bool(self.station_manager.is_available(station_id, current_time))
        except Exception:
            state = self._state(station_id)
            return not self._state_is_occupied(state)

    def _station_busy_until(self, station_id, current_time):
        current_time = self._safe_time(current_time, 0.0)
        state = self._state(station_id)
        if not self._state_is_occupied(state):
            return current_time
        occupied_until = self._state_occupied_until(state)
        if occupied_until is not None:
            return max(current_time, occupied_until)
        entry_time = self._state_entry_time(state)
        if entry_time is None:
            return current_time
        max_process_time = self._station_max_process_time(station_id)
        if max_process_time <= 0.0:
            max_process_time = self._station_min_process_time(station_id)
        return max(current_time, entry_time + max_process_time)

    def _physical_available_time(self, station_id, current_time):
        current_time = self._safe_time(current_time, 0.0)
        if self._station_is_available(station_id, current_time):
            return current_time
        return self._station_busy_until(station_id, current_time)

    def _reservation_available_time(self, station_id, current_time):
        current_time = self._safe_time(current_time, 0.0)
        if self.station_reservation_service is None:
            return current_time
        try:
            value = self.station_reservation_service.earliest_available_time(station_id=station_id, current_time=current_time)
        except Exception:
            return current_time
        value = self._finite_or_none(value)
        if value is None:
            return current_time
        return value

    def earliest_available_time(self, station_id, current_time):
        physical_time = self._physical_available_time(station_id, current_time)
        reservation_time = self._reservation_available_time(station_id, current_time)
        return max(physical_time, reservation_time)

    def _reservation_records(self, station_ids):
        if self.station_reservation_service is None:
            return []
        try:
            reservations = self.station_reservation_service.active_reservations(None)
        except Exception:
            return []
        station_ids = set((int(station_id) for station_id in station_ids))
        records = []
        for reservation in reservations:
            station_id = int(getattr(reservation, 'station_id', -1))
            if station_id not in station_ids:
                continue
            start_time = self._finite_or_none(getattr(reservation, 'start_time', None))
            if start_time is None:
                continue
            end_time = self._finite_or_none(getattr(reservation, 'end_time', None))
            records.append({'station_id': station_id, 'start_time': start_time, 'end_time': end_time})
        return records

    def _station_last_fill_time(self, station_id, current_time):
        state = self._state(station_id)
        if self._state_is_occupied(state):
            entry_time = self._state_entry_time(state)
            if entry_time is not None:
                return entry_time
        values = []
        for record in self._reservation_records([station_id]):
            if int(record['station_id']) != int(station_id):
                continue
            values.append(float(record['start_time']))
        if not values:
            return None
        return max(values)

    def _group_has_active_load(self, station_ids, current_time):
        current_time = self._safe_time(current_time, 0.0)
        for station_id in station_ids:
            state = self._state(station_id)
            if self._state_is_occupied(state):
                return True
        for record in self._reservation_records(station_ids):
            start_time = float(record['start_time'])
            end_time = record['end_time']
            if end_time is None:
                if start_time >= current_time:
                    return True
            elif start_time <= current_time <= end_time:
                return True
        return False

    def _group_busy_until(self, station_ids, current_time):
        current_time = self._safe_time(current_time, 0.0)
        values = []
        for station_id in station_ids:
            state = self._state(station_id)
            if not self._state_is_occupied(state):
                continue
            values.append(self._station_busy_until(station_id, current_time))
        for record in self._reservation_records(station_ids):
            start_time = float(record['start_time'])
            end_time = record['end_time']
            if end_time is not None:
                if end_time >= current_time:
                    values.append(end_time)
            elif start_time >= current_time:
                station_id = int(record['station_id'])
                duration = self._station_max_process_time(station_id)
                if duration <= 0.0:
                    duration = self._station_min_process_time(station_id)
                values.append(start_time + duration)
        if not values:
            return current_time
        return max(current_time, max(values))

    def earliest_group_availability(self, station_ids, current_time):
        current_time = self._safe_time(current_time, 0.0)
        values = []
        for station_id in station_ids:
            value = self._finite_or_none(self.earliest_available_time(station_id, current_time))
            if value is None:
                continue
            if value <= current_time:
                return None
            values.append(value)
        return min(values) if values else None

    def _last_selected_from_station_memory(self, station_ids):
        values = []
        for station_id in station_ids:
            station = self._station(station_id)
            if station is None:
                continue
            value = getattr(station, 'shared_bath_last_selected_station_id', None)
            if value is None:
                continue
            try:
                values.append(int(value))
            except Exception:
                pass
        if values:
            return values[-1]
        return None

    def _write_last_selected_to_station_memory(self, station_ids, selected_station):
        for station_id in station_ids:
            station = self._station(station_id)
            if station is None:
                continue
            station.shared_bath_last_selected_station_id = int(selected_station)

    def _latest_filled_station_in_group(self, station_ids, current_time):
        latest_station = None
        latest_time = None
        for station_id in station_ids:
            fill_time = self._station_last_fill_time(station_id, current_time)
            if fill_time is None:
                continue
            if latest_time is None or fill_time > latest_time:
                latest_time = fill_time
                latest_station = int(station_id)
        return (latest_station, latest_time)

    def _alternate_last_station(self, station_ids, current_time):
        latest_station, _latest_time = self._latest_filled_station_in_group(station_ids, current_time)
        if latest_station is not None:
            return latest_station
        station_memory = self._last_selected_from_station_memory(station_ids)
        if station_memory is not None:
            return station_memory
        group_key = self._group_key(station_ids)
        return self.last_selected_station_by_group.get(group_key, None)

    def _alternate_preferred_station_ids(self, station_ids, current_time):
        ordered = sorted([int(station_id) for station_id in station_ids])
        if len(ordered) <= 1:
            return ordered
        last_station = self._alternate_last_station(ordered, current_time)
        if last_station is None:
            return ordered
        if int(last_station) not in ordered:
            return ordered
        last_index = ordered.index(int(last_station))
        next_index = (last_index + 1) % len(ordered)
        preferred = [ordered[next_index]]
        remaining = [station_id for station_id in ordered if station_id not in preferred]
        return preferred + remaining

    def _last_active_group_fill_time(self, station_ids, current_time):
        fill_times = []
        for station_id in station_ids:
            fill_time = self._station_last_fill_time(station_id, current_time)
            if fill_time is not None:
                fill_times.append(fill_time)
        if not fill_times:
            return None
        return max(fill_times)

    def _recommended_group_time(self, station_ids, current_time):
        current_time = self._safe_time(current_time, 0.0)
        _group_name, mode, _value = self._stagger_rule_for_group(station_ids)
        if mode == 'alternate':
            if self._group_has_active_load(station_ids, current_time):
                return self._group_busy_until(station_ids, current_time)
            return current_time
        target_gap = self._target_gap(station_ids)
        if target_gap <= 0.0:
            return current_time
        last_fill_time = self._last_active_group_fill_time(station_ids, current_time)
        if last_fill_time is None:
            return current_time
        return max(current_time, last_fill_time + target_gap)

    def _score_station(self, station_id, current_time):
        available_time = self.earliest_available_time(station_id, current_time)
        last_fill_time = self._station_last_fill_time(station_id, current_time)
        if last_fill_time is None:
            last_fill_sort_value = -1000000000.0
        else:
            last_fill_sort_value = last_fill_time
        return (available_time, last_fill_sort_value)

    def _select_best_station_from_ordered_candidates(self, station_ids, current_time, strict_first=False):
        if not station_ids:
            return None
        if strict_first:
            selected = int(station_ids[0])
            debug_print(lambda: f'SHARED_BATH_CANDIDATE S={selected} available={self.earliest_available_time(selected, current_time)} last_fill={self._station_last_fill_time(selected, current_time)} strict_alternate=True')
            return selected
        best_station = None
        best_score = None
        for station_id in station_ids:
            score = self._score_station(station_id, current_time)
            debug_print(lambda: f'SHARED_BATH_CANDIDATE S={station_id} available={score[0]} last_fill={score[1]}')
            if best_station is None or score < best_score:
                best_station = int(station_id)
                best_score = score
        return best_station

    def select(self, station_ids, current_time):
        current_time = self._safe_time(current_time, 0.0)
        self.last_recommended_time = current_time
        if not station_ids:
            return None
        station_ids = [int(station_id) for station_id in station_ids]
        group_name, mode, value = self._stagger_rule_for_group(station_ids)
        if mode == 'alternate':
            group_busy = self._group_has_active_load(station_ids, current_time)
            if group_busy:
                retry_time = self._group_busy_until(station_ids, current_time)
                retry_time = self._safe_time(retry_time, current_time + self.ALTERNATE_RETRY_INTERVAL)
                retry_time = max(retry_time, current_time + self.ALTERNATE_RETRY_INTERVAL)
                self.last_recommended_time = retry_time
                debug_print(lambda: f'SHARED_BATH_BLOCKED group_name={group_name} group={station_ids} mode=alternate current={current_time:.1f} retry_at={retry_time:.1f} reason=GROUP_OCCUPIED')
                return None
            ordered_candidates = self._alternate_preferred_station_ids(station_ids, current_time)
            selected_station = int(ordered_candidates[0])
            self.last_recommended_time = current_time
            debug_print(lambda: f'SHARED_BATH_CANDIDATE S={selected_station} available={self.earliest_available_time(selected_station, current_time)} last_fill={self._station_last_fill_time(selected_station, current_time)} strict_alternate=True')
            debug_print(lambda: f'SHARED_BATH_ALTERNATE group_name={group_name} group={station_ids} busy=False ordered={ordered_candidates} selected={selected_station} recommended={current_time:.1f}')
        else:
            recommended_time = self._recommended_group_time(station_ids, current_time)
            recommended_time = self._safe_time(recommended_time, current_time)
            self.last_recommended_time = recommended_time
            selected_station = self._select_best_station_from_ordered_candidates(station_ids=station_ids, current_time=recommended_time, strict_first=False)
        if selected_station is None:
            return None
        group_key = self._group_key(station_ids)
        self.last_selected_station_by_group[group_key] = int(selected_station)
        self._write_last_selected_to_station_memory(station_ids=station_ids, selected_station=selected_station)
        debug_print(lambda: f'SHARED_BATH_STAGGER group_name={group_name} group={station_ids} mode={mode} value={value:.1f} current={current_time:.1f} recommended={self.last_recommended_time:.1f} gap={self._target_gap(station_ids):.1f} selected={selected_station}')
        return selected_station

    def recommended_time(self):
        return self.last_recommended_time
