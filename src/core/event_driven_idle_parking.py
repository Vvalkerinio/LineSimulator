from dataclasses import dataclass

from src.core.event_track_yield_planner import EventTrackYieldMove


@dataclass(frozen=True)
class EventDrivenIdleParkingPlan:
    station_id: int
    departure_time: float
    arrival_time: float
    approach_start_time: float
    replaced_yield: EventTrackYieldMove | None = None


class EventDrivenIdleParking:
    def __init__(
        self,
        manipulator_manager,
        station_manager,
        station_reservation_service,
        track_service,
        passing_detector,
        track_safety,
        required_spacing,
    ):
        self.manipulator_manager = manipulator_manager
        self.station_manager = station_manager
        self.station_reservation_service = station_reservation_service
        self.track_service = track_service
        self.passing_detector = passing_detector
        self.track_safety = track_safety
        self.required_spacing = max(0.0, float(required_spacing))

    @staticmethod
    def _zone(manipulator):
        start = int(getattr(manipulator, "work_zone_start", 1))
        end = int(getattr(manipulator, "work_zone_end", 999))
        return min(start, end), max(start, end)

    def plan(
        self,
        manipulator,
        source_station,
        target_station,
        hanger_id,
        current_position,
        available_time,
        pickup_finish_time,
        stations,
    ):
        if self.required_spacing <= 0.0:
            return None

        own_id = int(manipulator.id)
        own_start, own_end = self._zone(manipulator)
        safe_bounds = []
        for neighbor in self.manipulator_manager.all():
            if int(neighbor.id) == own_id:
                continue
            neighbor_start, neighbor_end = self._zone(neighbor)
            if own_id < int(neighbor.id):
                safe_bounds.append(("left", neighbor_start - self.required_spacing))
            else:
                safe_bounds.append(("right", neighbor_end + self.required_spacing))

        if not safe_bounds:
            return None
        if not any(
            (side == "left" and float(current_position) > bound)
            or (side == "right" and float(current_position) < bound)
            for side, bound in safe_bounds
        ):
            return None

        candidates = []
        for station in stations:
            station_id = int(station.id)
            if station_id in (int(source_station), int(target_station)):
                continue
            if not bool(getattr(station, "enabled", True)):
                continue
            if not own_start <= station_id <= own_end:
                continue
            if any(
                (side == "left" and station_id > bound + 1e-9)
                or (side == "right" and station_id < bound - 1e-9)
                for side, bound in safe_bounds
            ):
                continue
            candidates.append(station_id)

        if not candidates:
            return None

        def clearance_score(station_id):
            return sum(
                abs(float(station_id) - bound)
                for _side, bound in safe_bounds
            )

        candidates.sort(key=lambda station_id: (clearance_score(station_id), station_id))
        departure_time = float(available_time)
        travel_time = float(manipulator.travel_time_per_position)
        for station_id in candidates:
            arrival_time = departure_time + abs(
                float(current_position) - float(station_id)
            ) * travel_time
            if not self.station_manager.is_available(station_id, arrival_time):
                continue
            if self.station_reservation_service is not None and not self.station_reservation_service.can_reserve(
                station_id=station_id,
                hanger_id=int(hanger_id),
                start_time=arrival_time,
            ):
                continue
            approach_start_time = float(pickup_finish_time) - abs(
                float(source_station) - float(station_id)
            ) * travel_time
            if arrival_time + 1e-9 >= approach_start_time:
                continue

            moves = (
                (float(current_position), float(station_id), departure_time, arrival_time),
                (float(station_id), float(station_id), arrival_time, approach_start_time),
                (
                    float(station_id),
                    float(source_station),
                    approach_start_time,
                    float(pickup_finish_time),
                ),
            )
            if any(
                self.track_safety.conflict_for_move(
                    manipulator_id=own_id,
                    start_position=start_position,
                    end_position=end_position,
                    start_time=start_time,
                    end_time=end_time,
                    required_gap=self.required_spacing,
                )
                is not None
                for start_position, end_position, start_time, end_time in moves
            ):
                continue
            if any(
                start != end
                and (
                    not self.track_service.can_reserve(
                        manipulator_id=own_id,
                        source_station=int(round(start)),
                        target_station=int(round(end)),
                        start_time=start_time,
                        travel_time_per_position=travel_time,
                    )
                    or not self.passing_detector.transport_allowed(
                        manipulator_id=own_id,
                        start_position=start,
                        target_position=end,
                        start_time=start_time,
                        finish_time=end_time,
                    )
                )
                for start, end, start_time, end_time in moves
            ):
                continue

            return EventDrivenIdleParkingPlan(
                station_id=station_id,
                departure_time=departure_time,
                arrival_time=arrival_time,
                approach_start_time=approach_start_time,
            )
        return None
