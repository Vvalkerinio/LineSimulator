from src.model.station_numbering import display_station_id
from src.core.simulation_debug import debug_print
from dataclasses import dataclass

@dataclass
class StationReservation:
    station_id: int
    hanger_id: int
    start_time: float
    end_time: float | None = None
    source: str = ''

class StationReservationService:

    def __init__(self):
        self._reservations = []

    def _active_at(self, reservation, time_value: float) -> bool:
        if time_value < reservation.start_time:
            return False
        if reservation.end_time is None:
            return True
        return time_value < reservation.end_time

    def _overlaps_open_interval(self, reservation, start_time: float) -> bool:
        if reservation.end_time is not None and reservation.end_time <= start_time:
            return False
        return True

    def can_reserve(self, station_id: int, hanger_id: int, start_time: float) -> bool:
        for reservation in self._reservations:
            if reservation.station_id != station_id:
                continue
            if reservation.hanger_id == hanger_id:
                continue
            if self._overlaps_open_interval(reservation, start_time):
                return False
        return True

    def reserve(self, station_id: int, hanger_id: int, start_time: float, source: str='transport_target') -> bool:
        if not self.can_reserve(station_id, hanger_id, start_time):
            return False
        existing = self._find_open_reservation(station_id, hanger_id)
        if existing is not None:
            existing.start_time = min(existing.start_time, start_time)
            return True
        self._reservations.append(StationReservation(station_id=station_id, hanger_id=hanger_id, start_time=start_time, end_time=None, source=source))
        debug_print(lambda: f'STATION RESERVE S={display_station_id(station_id)} H={hanger_id} from={start_time:.1f}')
        return True

    def _find_open_reservation(self, station_id: int, hanger_id: int):
        candidates = [reservation for reservation in self._reservations if reservation.station_id == station_id and reservation.hanger_id == hanger_id and (reservation.end_time is None)]
        if not candidates:
            return None
        candidates.sort(key=lambda item: item.start_time, reverse=True)
        return candidates[0]

    def release_at(self, station_id: int, hanger_id: int, release_time: float) -> None:
        reservation = self._find_open_reservation(station_id, hanger_id)
        if reservation is None:
            return
        reservation.end_time = release_time
        debug_print(lambda: f'STATION RELEASE_AT S={display_station_id(station_id)} H={hanger_id} until={release_time:.1f}')

    def earliest_available_time(self, station_id: int, current_time: float) -> float:
        available_time = current_time
        for reservation in self._reservations:
            if reservation.station_id != station_id:
                continue
            if reservation.end_time is None:
                if reservation.start_time <= current_time:
                    return float('inf')
                available_time = max(available_time, reservation.start_time)
                continue
            if reservation.end_time > current_time:
                available_time = max(available_time, reservation.end_time)
        return available_time

    def active_reservations(self, time_value: float | None=None):
        if time_value is None:
            return list(self._reservations)
        return [reservation for reservation in self._reservations if self._active_at(reservation, time_value)]

    def generate_summary(self) -> str:
        lines = []
        lines.append('=' * 60)
        lines.append('STATION RESERVATION SUMMARY')
        lines.append('=' * 60)
        if not self._reservations:
            lines.append('No station reservations.')
            lines.append('=' * 60)
            return '\n'.join(lines)
        for reservation in self._reservations:
            end_text = 'open' if reservation.end_time is None else f'{reservation.end_time:.1f}'
            lines.append(f'S={display_station_id(reservation.station_id)} H={reservation.hanger_id} from={reservation.start_time:.1f} to={end_text} source={reservation.source}')
        lines.append('=' * 60)
        return '\n'.join(lines)

    def print_summary(self):
        debug_print(lambda: '')
        debug_print(lambda: self.generate_summary())
