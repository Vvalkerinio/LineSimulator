from src.core.simulation_debug import debug_print
from src.model.event import Event
from src.model.event_type import EventType

class PredictivePickupScheduler:

    def __init__(self, config, route, station_map, engine, state):
        self.config = config
        self.route = route
        self.station_map = station_map
        self.engine = engine
        self.state = state
        self.planned_checks = set()
        self.lookahead_time = float(getattr(config, 'predictive_pickup_lookahead_time', 160.0))

    def _as_int_set(self, value, default):
        if value is None:
            return set(default)
        if isinstance(value, set):
            return {int(item) for item in value}
        if isinstance(value, list) or isinstance(value, tuple):
            return {int(item) for item in value}
        text = str(value).strip()
        if not text:
            return set(default)
        result = set()
        for part in text.split(','):
            part = part.strip()
            if not part:
                continue
            try:
                result.add(int(part))
            except ValueError:
                continue
        if not result:
            return set(default)
        return result

    def horizon_enabled(self):
        return bool(getattr(self.config, 'predictive_pickup_horizon_enabled', True))

    def horizon_time(self):
        return float(getattr(self.config, 'predictive_pickup_horizon_time', 60.0))

    def horizon_station_ids(self):
        return self._as_int_set(getattr(self.config, 'predictive_pickup_horizon_station_ids', None), default=[19, 20, 21])

    def no_horizon_station_ids(self):
        return self._as_int_set(getattr(self.config, 'predictive_pickup_no_horizon_station_ids', None), default=[3, 4])

    def commit_horizon_for_station(self, station_id):
        station_id = int(station_id)
        if not self.horizon_enabled():
            return 0.0
        if station_id in self.no_horizon_station_ids():
            return 0.0
        if station_id not in self.horizon_station_ids():
            return 0.0
        return self.horizon_time()

    def _is_candidate_station(self, station_id):
        if not self.route:
            return False
        if station_id == self.route[0]:
            return False
        if station_id == self.route[-1]:
            return False
        station = self.station_map.get(station_id)
        if station is None:
            return False
        if not getattr(station, 'enabled', True):
            return False
        min_time = getattr(station, 'min_process_time', 0.0)
        max_time = getattr(station, 'max_process_time', 0.0)
        if min_time is None or max_time is None:
            return False
        if min_time <= 0 or max_time <= 0 or max_time >= 9999:
            return False
        return True

    def ready_time(self, station_id, entry_time):
        station = self.station_map.get(station_id)
        if station is None:
            return None
        min_time = float(getattr(station, 'min_process_time', 0.0))
        return entry_time + min_time

    def latest_pickup_time(self, station_id, entry_time):
        station = self.station_map.get(station_id)
        if station is None:
            return None
        max_time = float(getattr(station, 'max_process_time', 0.0))
        return entry_time + max_time

    def schedule_check(self, hanger_id, station_id, entry_time):
        if not self._is_candidate_station(station_id):
            return
        key = (hanger_id, station_id)
        if key in self.planned_checks:
            return
        ready_time = self.ready_time(station_id, entry_time)
        latest_time = self.latest_pickup_time(station_id, entry_time)
        if ready_time is None:
            return
        check_time = max(entry_time, ready_time - self.lookahead_time)
        self.planned_checks.add(key)
        self.engine.schedule(Event(check_time, EventType.PREDICTIVE_PICKUP_CHECK, None, hanger_id, station_id, station_id))
        debug_print(lambda: f'PREDICTIVE_PICKUP_CHECK_SCHEDULED H={hanger_id} S={station_id} entry={entry_time:.1f} ready={ready_time:.1f} latest={latest_time:.1f} check={check_time:.1f}')

    def station_still_contains_hanger(self, station_manager, hanger_id, station_id):
        try:
            state = station_manager.state(station_id)
        except Exception:
            return False
        return getattr(state, 'hanger_id', None) == hanger_id

    def next_station_for(self, hanger_id, station_id):
        current_index = self.state.hanger_route_index.get(hanger_id)
        if current_index is None:
            return None
        next_index = current_index + 1
        if next_index >= len(self.route):
            return None
        return self.route[next_index]
