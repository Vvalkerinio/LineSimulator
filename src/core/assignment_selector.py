from src.core.simulation_debug import debug_print
from src.model.manipulator_assignment import ManipulatorAssignment

class AssignmentSelector:
    TRACK_SEARCH_STEP = 5.0
    MAX_TRACK_DELAY = 300.0
    DEADLINE_LATE_PENALTY = 1000000.0
    DEADLINE_NEAR_WINDOW = 60.0
    DEADLINE_NEAR_PENALTY = 1000.0
    EDF_WEIGHT = 100000.0

    def __init__(self, manipulator_manager, availability, transport_engine, stations=None):
        self.manipulator_manager = manipulator_manager
        self.availability = availability
        self.transport_engine = transport_engine
        self.pending_yield_proposal = None
        self.station_map = {
            int(station.id): station for station in (stations or [])
        }

    def _current_position(self, manipulator, time_value):
        if hasattr(self.transport_engine, 'position_at'):
            return self.transport_engine.position_at(manipulator, time_value)
        return manipulator.position

    def _travel_time(self, manipulator, source_station: int, target_station: int) -> float:
        if source_station == target_station:
            return 0.0
        if hasattr(manipulator, 'transport_time'):
            return manipulator.transport_time(source_station, target_station)
        if hasattr(manipulator, 'travel_time'):
            return manipulator.travel_time(source_station, target_station)
        return abs(target_station - source_station) * manipulator.travel_time_per_position

    def _zone_start(self, manipulator):
        return int(getattr(manipulator, 'work_zone_start', 1))

    def _zone_end(self, manipulator):
        return int(getattr(manipulator, 'work_zone_end', 999))

    def _position_inside_zone(self, manipulator, position) -> bool:
        return self._zone_start(manipulator) <= position <= self._zone_end(manipulator)

    def _is_allowed_by_work_zone(self, manipulator, source_station: int, target_station: int) -> bool:
        return self._position_inside_zone(manipulator, source_station) and self._position_inside_zone(manipulator, target_station)

    def _home_position(self, manipulator):
        return int(getattr(manipulator, 'parking_position', getattr(manipulator, 'position', 1)))

    def _target_is_handoff_position(self, manipulator, target_station: int) -> bool:
        for other in self.manipulator_manager.all():
            if other.id == manipulator.id:
                continue
            other_start = self._zone_start(other)
            other_end = self._zone_end(other)
            if other_start <= target_station <= other_end:
                return True
        return False

    def _candidate_yield_positions(self, manipulator, blocked_position: int):
        zone_start = self._zone_start(manipulator)
        zone_end = self._zone_end(manipulator)
        candidates = []
        home = self._home_position(manipulator)
        if zone_start <= home <= zone_end and home != blocked_position:
            candidates.append(home)
        for distance in range(1, max(blocked_position - zone_start, zone_end - blocked_position) + 1):
            left = blocked_position - distance
            right = blocked_position + distance
            if zone_start <= left <= zone_end and left != blocked_position:
                candidates.append(left)
            if zone_start <= right <= zone_end and right != blocked_position:
                candidates.append(right)
        unique = []
        for value in candidates:
            if value not in unique:
                unique.append(value)
        return unique

    def _non_process_return_positions(
        self, manipulator, source_station, target_station
    ):
        candidates = []
        for station_id, station in self.station_map.items():
            if not bool(getattr(station, "enabled", True)):
                continue
            if bool(getattr(station, "is_process_bath", True)):
                continue
            if not self._position_inside_zone(manipulator, station_id):
                continue
            # Do not return to the just-vacated source. In particular this
            # prevents parking over the load position after LOAD -> ODT.
            if int(station_id) == int(source_station):
                continue
            candidates.append(station_id)
        preferred = int(getattr(
            manipulator,
            "preferred_parking_position",
            self._home_position(manipulator)
        ))
        return sorted(candidates, key=lambda position: (
            0 if int(position) == preferred else 1,
            abs(int(position) - int(target_station)),
            abs(int(position) - preferred),
            int(position)
        ))

    def _return_position_after_drop(self, manipulator, source_station: int, target_station: int):
        # Transport kończy się fizycznie na DROP. Parking ani YIELD nie są
        # automatycznym ogonem zadania produkcyjnego. Ruch odblokowujący jest
        # proponowany i commitowany osobno przez EventTrackYieldPlanner dopiero
        # dla konkretnego konfliktu. Zapobiega to return_move do pozycji, która
        # w chwili planowania wygląda na wolną, lecz jest miejscem postoju
        # sąsiada w późniejszej wersji harmonogramu.
        return int(target_station)

    def _return_position_candidates(self, manipulator, source_station, target_station):
        # Jedyny endpoint transportu produkcyjnego to stanowisko DROP.
        # Alternatywne parkingi są obsługiwane wyłącznie przez osobny planner.
        return [int(target_station)]

    def _build_assignment(self, manipulator, source_station: int, target_station: int, start_time: float, return_position=None):
        current_position = self._current_position(manipulator, start_time)
        pickup_time = abs(current_position - source_station) * manipulator.travel_time_per_position
        loaded_travel_time = self._travel_time(manipulator, source_station, target_station)
        pickup_start_time = start_time
        pickup_finish_time = pickup_start_time + pickup_time
        transport_start_time = pickup_finish_time + manipulator.lift_time
        transport_finish_time = transport_start_time + loaded_travel_time + manipulator.drop_time
        if return_position is None:
            return_position = self._return_position_after_drop(
                manipulator, source_station, target_station
            )
        return_start_time = transport_finish_time
        return_travel_time = self._travel_time(manipulator, target_station, return_position)
        return_finish_time = return_start_time + return_travel_time
        return ManipulatorAssignment(manipulator_id=manipulator.id, source_station=source_station, target_station=target_station, pickup_start_time=pickup_start_time, pickup_finish_time=pickup_finish_time, transport_start_time=transport_start_time, transport_finish_time=transport_finish_time, return_position=return_position, return_start_time=return_start_time, return_finish_time=return_finish_time)

    def _assignment_is_valid(self, manipulator, assignment, start_time: float) -> bool:
        current_position = self._current_position(manipulator, start_time)
        if not self.transport_engine.validate_order(manipulator, assignment.target_station, start_time):
            return False
        if hasattr(self.transport_engine, 'validate_assignment_track'):
            if not self.transport_engine.validate_assignment_track(manipulator=manipulator, current_position=current_position, assignment=assignment):
                return False
        elif not self.transport_engine.validate_track(manipulator, assignment.source_station, assignment.target_station, assignment.transport_start_time):
            return False
        if hasattr(self.transport_engine, 'validate_static_occupancy'):
            if not self.transport_engine.validate_static_occupancy(manipulator, current_position, assignment.source_station, assignment.target_station, assignment.pickup_start_time, assignment.pickup_finish_time, assignment.transport_start_time, assignment.transport_finish_time, assignment.return_position, assignment.return_start_time, assignment.return_finish_time):
                return False
        if not self.transport_engine.validate_passing(manipulator, assignment.pickup_start_time, assignment.return_finish_time):
            return False
        return True

    def _next_candidate_time_for_earliest_pickup(self, assignment, earliest_pickup_time, candidate_time):
        if earliest_pickup_time is None:
            return None
        if assignment.pickup_finish_time >= earliest_pickup_time:
            return None
        delta = earliest_pickup_time - assignment.pickup_finish_time
        return candidate_time + max(self.TRACK_SEARCH_STEP, delta)

    def _next_candidate_time_for_earliest_transport_finish(self, assignment, earliest_transport_finish_time, candidate_time):
        if earliest_transport_finish_time is None:
            return None
        if assignment.transport_finish_time >= earliest_transport_finish_time:
            return None
        delta = earliest_transport_finish_time - assignment.transport_finish_time
        return candidate_time + max(self.TRACK_SEARCH_STEP, delta)

    def _find_best_assignment_for_manipulator(self, manipulator, source_station: int, target_station: int, current_time: float, earliest_pickup_time: float | None=None, earliest_transport_finish_time: float | None=None, allow_yield: bool=False):
        if not self._is_allowed_by_work_zone(manipulator, source_station, target_station):
            return None
        earliest_time = max(current_time, self.availability.available_from(manipulator.id))
        candidate_time = earliest_time
        max_time = earliest_time + self.MAX_TRACK_DELAY
        while candidate_time <= max_time:
            assignments = [
                self._build_assignment(
                    manipulator=manipulator,
                    source_station=source_station,
                    target_station=target_station,
                    start_time=candidate_time,
                    return_position=position
                )
                for position in self._return_position_candidates(
                    manipulator, source_station, target_station
                )
            ]
            next_candidate_time = self._next_candidate_time_for_earliest_pickup(
                assignment=assignments[0],
                earliest_pickup_time=earliest_pickup_time,
                candidate_time=candidate_time
            )
            if next_candidate_time is None:
                next_candidate_time = (
                    self._next_candidate_time_for_earliest_transport_finish(
                        assignment=assignments[0],
                        earliest_transport_finish_time=earliest_transport_finish_time,
                        candidate_time=candidate_time
                    )
                )
            if next_candidate_time is not None:
                candidate_time = next_candidate_time
                continue
            for assignment in assignments:
                if self._assignment_is_valid(
                    manipulator=manipulator,
                    assignment=assignment,
                    start_time=candidate_time
                ):
                    return assignment
            if allow_yield and hasattr(self.transport_engine, 'propose_yield'):
                proposal = self.transport_engine.propose_yield(
                    blocked_target=source_station,
                    current_time=current_time
                )
                if proposal is not None:
                    # Candidate evaluation is side-effect free. The caller may
                    # commit this single proposal and retry after YIELD_END.
                    self.pending_yield_proposal = proposal
                    return None
            candidate_time += self.TRACK_SEARCH_STEP
        return None

    def _deadline_penalty(self, assignment, latest_pickup_time):
        if latest_pickup_time is None:
            return 0.0
        slack = latest_pickup_time - assignment.pickup_finish_time
        if slack < 0:
            return self.DEADLINE_LATE_PENALTY + abs(slack) * self.DEADLINE_NEAR_PENALTY
        if slack < self.DEADLINE_NEAR_WINDOW:
            return (self.DEADLINE_NEAR_WINDOW - slack) * self.DEADLINE_NEAR_PENALTY
        return 0.0

    def _assignment_score(self, manipulator, assignment, latest_pickup_time=None) -> float:
        if latest_pickup_time is not None:
            slack = latest_pickup_time - assignment.pickup_finish_time
            if slack < 0:
                return 1000000.0 + abs(slack) * 10000.0 + assignment.pickup_finish_time
            return -slack * 1000.0 + assignment.pickup_finish_time
        return assignment.return_finish_time

    def consume_pending_yield_proposal(self):
        proposal = self.pending_yield_proposal
        self.pending_yield_proposal = None
        return proposal

    def select(self, source_station: int, target_station: int, current_time: float, latest_pickup_time: float | None=None, earliest_pickup_time: float | None=None, earliest_transport_finish_time: float | None=None):
        self.pending_yield_proposal = None
        best_assignment = None
        best_score = None
        for manipulator in self.manipulator_manager.all():
            assignment = self._find_best_assignment_for_manipulator(manipulator=manipulator, source_station=source_station, target_station=target_station, current_time=current_time, earliest_pickup_time=earliest_pickup_time, earliest_transport_finish_time=earliest_transport_finish_time, allow_yield=False)
            if assignment is None:
                continue
            score = self._assignment_score(manipulator, assignment, latest_pickup_time)
            if latest_pickup_time is not None:
                slack = latest_pickup_time - assignment.pickup_finish_time
                debug_print(lambda: f'DEADLINE_ASSIGNMENT M={manipulator.id} {source_station}->{target_station} pickup={assignment.pickup_finish_time:.1f} latest={latest_pickup_time:.1f} slack={slack:.1f} score={score:.1f}')
            if earliest_pickup_time is not None:
                early_margin = assignment.pickup_finish_time - earliest_pickup_time
                debug_print(lambda: f'EARLIEST_PICKUP_CHECK M={manipulator.id} {source_station}->{target_station} pickup={assignment.pickup_finish_time:.1f} earliest={earliest_pickup_time:.1f} margin={early_margin:.1f}')
            if best_assignment is None or score < best_score:
                best_assignment = assignment
                best_score = score
        if best_assignment is None:
            for manipulator in self.manipulator_manager.all():
                assignment = self._find_best_assignment_for_manipulator(manipulator=manipulator, source_station=source_station, target_station=target_station, current_time=current_time, earliest_pickup_time=earliest_pickup_time, earliest_transport_finish_time=earliest_transport_finish_time, allow_yield=True)
                if assignment is not None:
                    best_assignment = assignment
                    break
        if best_assignment is None:
            debug_print(lambda: f'BLOCKED {source_station}->{target_station}')
            return None
        return best_assignment
