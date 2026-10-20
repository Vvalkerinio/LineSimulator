from src.core.simulation_debug import debug_print
import math
from src.model.scheduled_transport import ScheduledTransport

class TransportScheduler:

    def __init__(self, assignment_selector, station_reservation_service=None):
        self.assignment_selector = assignment_selector
        self.station_reservation_service = station_reservation_service

    def set_station_reservation_service(self, station_reservation_service):
        self.station_reservation_service = station_reservation_service

    def _is_finite_number(self, value):
        try:
            value = float(value)
        except Exception:
            return False
        return math.isfinite(value)

    def _assignment_is_valid(self, assignment):
        if assignment is None:
            return False
        required_fields = ['manipulator_id', 'pickup_start_time', 'pickup_finish_time', 'transport_start_time', 'transport_finish_time']
        for field_name in required_fields:
            if not hasattr(assignment, field_name):
                return False
        time_fields = ['pickup_start_time', 'pickup_finish_time', 'transport_start_time', 'transport_finish_time']
        for field_name in time_fields:
            if not self._is_finite_number(getattr(assignment, field_name)):
                debug_print(lambda: f'SCHEDULER INVALID ASSIGNMENT {field_name}={getattr(assignment, field_name, None)}')
                return False
        return True

    def _target_station_can_be_reserved(self, hanger_id: int, target_station: int, drop_time: float) -> bool:
        if not self._is_finite_number(drop_time):
            return False
        if self.station_reservation_service is None:
            return True
        return self.station_reservation_service.can_reserve(station_id=target_station, hanger_id=hanger_id, start_time=drop_time)

    def reserve_target_station(self, hanger_id: int, target_station: int, drop_time: float) -> bool:
        if not self._is_finite_number(drop_time):
            return False
        if self.station_reservation_service is None:
            return True
        return self.station_reservation_service.reserve(station_id=target_station, hanger_id=hanger_id, start_time=drop_time, source='scheduled_transport')

    def release_source_station_at_pickup(self, hanger_id: int, source_station: int, pickup_time: float):
        if not self._is_finite_number(pickup_time):
            return
        if self.station_reservation_service is None:
            return
        self.station_reservation_service.release_at(station_id=source_station, hanger_id=hanger_id, release_time=pickup_time)

    def _select_assignment(self, source_station, target_station, current_time, latest_pickup_time=None, earliest_pickup_time=None, earliest_transport_finish_time=None):
        try:
            return self.assignment_selector.select(source_station=source_station, target_station=target_station, current_time=current_time, latest_pickup_time=latest_pickup_time, earliest_pickup_time=earliest_pickup_time, earliest_transport_finish_time=earliest_transport_finish_time)
        except TypeError:
            try:
                return self.assignment_selector.select(source_station=source_station, target_station=target_station, current_time=current_time, latest_pickup_time=latest_pickup_time, earliest_pickup_time=earliest_pickup_time)
            except TypeError:
                return self.assignment_selector.select(source_station=source_station, target_station=target_station, current_time=current_time)

    def schedule(self, hanger_id: int, source_station: int, target_station: int, current_time: float, latest_pickup_time: float | None=None, earliest_pickup_time: float | None=None, earliest_transport_finish_time: float | None=None):
        if target_station is None:
            debug_print(lambda: f'SCHEDULE BLOCKED H={hanger_id} SRC={source_station} DST=None T={current_time} reason=NO_TARGET_STATION')
            return None
        if not self._is_finite_number(current_time):
            debug_print(lambda: f'SCHEDULE BLOCKED H={hanger_id} SRC={source_station} DST={target_station} T={current_time} reason=NON_FINITE_CURRENT_TIME')
            return None
        assignment = self._select_assignment(source_station=source_station, target_station=target_station, current_time=current_time, latest_pickup_time=latest_pickup_time, earliest_pickup_time=earliest_pickup_time, earliest_transport_finish_time=earliest_transport_finish_time)
        if not self._assignment_is_valid(assignment):
            debug_print(lambda: f'SCHEDULE BLOCKED H={hanger_id} SRC={source_station} DST={target_station} T={current_time:.1f} reason=INVALID_ASSIGNMENT')
            return None
        if latest_pickup_time is not None and self._is_finite_number(latest_pickup_time):
            slack = float(latest_pickup_time) - float(assignment.pickup_finish_time)
            if slack < 0:
                debug_print(lambda: f'DEADLINE VIOLATION RISK H={hanger_id} SRC={source_station} DST={target_station} pickup={assignment.pickup_finish_time:.1f} latest={latest_pickup_time:.1f} late={abs(slack):.1f}')
            elif slack < 30:
                debug_print(lambda: f'DEADLINE WARNING H={hanger_id} SRC={source_station} DST={target_station} pickup={assignment.pickup_finish_time:.1f} latest={latest_pickup_time:.1f} slack={slack:.1f}')
        if earliest_pickup_time is not None and self._is_finite_number(earliest_pickup_time) and (float(assignment.pickup_finish_time) < float(earliest_pickup_time)):
            debug_print(lambda: f'EARLY PICKUP BLOCKED H={hanger_id} SRC={source_station} DST={target_station} pickup={assignment.pickup_finish_time:.1f} earliest={earliest_pickup_time:.1f}')
            return None
        drop_time = float(assignment.transport_finish_time)
        if not self._target_station_can_be_reserved(hanger_id=hanger_id, target_station=target_station, drop_time=drop_time):
            debug_print(lambda: f'TARGET RESERVED H={hanger_id} S={target_station} drop={drop_time:.1f}')
            return None
        return ScheduledTransport(hanger_id=hanger_id, source_station=source_station, target_station=target_station, manipulator_id=assignment.manipulator_id, pickup_start_time=assignment.pickup_start_time, pickup_finish_time=assignment.pickup_finish_time, transport_start_time=assignment.transport_start_time, transport_finish_time=assignment.transport_finish_time, return_position=assignment.return_position, return_start_time=assignment.return_start_time, return_finish_time=assignment.return_finish_time)
