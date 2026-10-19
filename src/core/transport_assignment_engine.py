from src.core.event_track_safety_coordinator import (
    EventTrackSafetyCoordinator,
    EventTrackConflict
)
from src.core.event_track_yield_planner import EventTrackYieldPlanner

class TransportAssignmentEngine:

    def __init__(
        self,
        manipulator_manager,
        availability,
        track_service,
        trajectory_manager,
        passing_detector
    ):
        self.manipulator_manager = (
            manipulator_manager
        )

        self.availability = (
            availability
        )

        self.track_service = (
            track_service
        )

        self.trajectory_manager = (
            trajectory_manager
        )

        self.passing_detector = (
            passing_detector
        )

        self.track_safety = EventTrackSafetyCoordinator(
            self.manipulator_manager,
            self.trajectory_manager
        )
        self.minimum_manipulator_spacing = 0.0
        self.last_track_conflict = None
        self.prevented_track_conflicts = []
        self.yield_planner = EventTrackYieldPlanner(
            self.manipulator_manager,
            self.availability,
            self.trajectory_manager,
            self.track_safety
        )

    def position_at(
        self,
        manipulator,
        time_value: float
    ):
        position = None

        if hasattr(
            self.trajectory_manager,
            "position_at"
        ):
            position = (
                self.trajectory_manager
                .position_at(
                    manipulator.id,
                    time_value
                )
            )

        if (
            position is None
            or
            position == 0
        ):
            position = (
                manipulator.position
            )

        return (
            position
        )

    def _position_inside_path(
        self,
        position,
        start_position,
        end_position
    ) -> bool:
        if (
            start_position
            ==
            end_position
        ):
            return False

        low = min(
            start_position,
            end_position
        )

        high = max(
            start_position,
            end_position
        )

        #
        # Zakres otwarty.
        #
        # Celowo NIE blokujemy pozycji dokładnie na granicy ruchu,
        # bo pozycje graniczne są często punktami przekazania detalu
        # między manipulatorami.
        #
        # Przykład:
        # M2 wykonuje 8 -> 14
        # M3 później wykonuje 14 -> 15
        #
        # Sama obecność pozycji 14 na końcu ruchu nie może blokować
        # całego przepływu. Zwalnianie takiej pozycji ma robić
        # yield_move/return_move generowany w assignment_selector.py.
        #
        return (
            low
            <
            position
            <
            high
        )

    def _sample_times(
        self,
        start_time,
        end_time
    ):
        if (
            end_time
            <= start_time
        ):
            return [
                start_time
            ]

        middle = (
            start_time
            +
            (
                end_time
                -
                start_time
            )
            / 2.0
        )

        return [
            start_time,
            middle,
            end_time
        ]

    def _path_blocked_by_other_manipulator(
        self, manipulator, start_position, end_position, start_time, end_time
    ) -> bool:
        travel_end = min(
            float(end_time),
            float(start_time) + abs(float(end_position) - float(start_position))
            * float(manipulator.travel_time_per_position)
        )
        conflict = self.track_safety.conflict_for_move(
            manipulator_id=int(manipulator.id),
            start_position=float(start_position),
            end_position=float(end_position),
            start_time=float(start_time),
            end_time=float(travel_end),
            required_gap=float(self.minimum_manipulator_spacing)
        )
        if conflict is None and float(end_time) > travel_end:
            conflict = self.track_safety.conflict_for_move(
                manipulator_id=int(manipulator.id),
                start_position=float(end_position),
                end_position=float(end_position),
                start_time=float(travel_end),
                end_time=float(end_time),
                required_gap=float(self.minimum_manipulator_spacing)
            )
        self.last_track_conflict = conflict
        if conflict is not None:
            self.prevented_track_conflicts.append(conflict)
        return conflict is not None

    def propose_yield(self, blocked_target, current_time):
        return self.yield_planner.propose(
            conflict=self.last_track_conflict,
            blocked_target=blocked_target,
            current_time=current_time,
            required_gap=self.minimum_manipulator_spacing
        )

    def commit_yield(self, move):
        return self.yield_planner.commit(move)

    def try_plan_yield(self, blocked_target, current_time):
        return self.yield_planner.plan(
            conflict=self.last_track_conflict,
            blocked_target=blocked_target,
            current_time=current_time,
            required_gap=self.minimum_manipulator_spacing
        )

    def validate_static_occupancy(
        self,
        manipulator,
        current_position,
        source_station,
        target_station,
        pickup_start_time,
        pickup_finish_time,
        transport_start_time,
        transport_finish_time,
        return_position=None,
        return_start_time=None,
        return_finish_time=None
    ) -> bool:
        #
        # 1. Pusty dojazd manipulatora:
        #
        # current_position -> source_station
        #
        empty_move_blocked = (
            self._path_blocked_by_other_manipulator(
                manipulator,
                current_position,
                source_station,
                pickup_start_time,
                pickup_finish_time
            )
        )

        if empty_move_blocked:
            return False

        #
        # 2. Przejazd z zawieszką:
        #
        # source_station -> target_station
        #
        loaded_move_blocked = (
            self._path_blocked_by_other_manipulator(
                manipulator,
                source_station,
                target_station,
                transport_start_time,
                transport_finish_time
            )
        )

        if loaded_move_blocked:
            return False

        #
        # 3. Ruch powrotny / yield move / parking move:
        #
        # target_station -> return_position
        #
        # Ten ruch jest kluczowy przy punktach przekazania.
        # Np. M2 odkłada na 14 i odjeżdża na 12,
        # żeby M3 mógł później wykonać 14 -> 15.
        #
        if (
            return_position is not None
            and
            return_start_time is not None
            and
            return_finish_time is not None
            and
            return_position != target_station
        ):
            return_move_blocked = (
                self._path_blocked_by_other_manipulator(
                    manipulator,
                    target_station,
                    return_position,
                    return_start_time,
                    return_finish_time
                )
            )

            if return_move_blocked:
                return False

        for other_id in getattr(self.trajectory_manager, "_segments_by_manipulator", {}):
            if int(other_id) == int(manipulator.id):
                continue
            try:
                other_position = float(self.trajectory_manager.position_at(other_id, return_finish_time or transport_finish_time))
            except Exception:
                continue
            my_position = float(return_position if return_position is not None else target_station)
            if abs(my_position - other_position) < float(self.minimum_manipulator_spacing):
                return False

        return True

    def validate_track(
        self,
        manipulator,
        source_station,
        target_station,
        start_time
    ):
        if (
            source_station
            ==
            target_station
        ):
            return True

        return (
            self.track_service.can_reserve(
                manipulator_id=(
                    manipulator.id
                ),
                source_station=(
                    source_station
                ),
                target_station=(
                    target_station
                ),
                start_time=(
                    start_time
                ),
                travel_time_per_position=(
                    manipulator.travel_time_per_position
                )
            )
        )

    def validate_assignment_track(
        self,
        manipulator,
        current_position,
        assignment
    ) -> bool:
        #
        # 1. Rezerwacja pustego dojazdu:
        #
        # current_position -> source_station
        #
        if (
            current_position
            != assignment.source_station
        ):
            empty_ok = (
                self.track_service.can_reserve(
                    manipulator_id=(
                        manipulator.id
                    ),
                    source_station=(
                        current_position
                    ),
                    target_station=(
                        assignment.source_station
                    ),
                    start_time=(
                        assignment.pickup_start_time
                    ),
                    travel_time_per_position=(
                        manipulator.travel_time_per_position
                    )
                )
            )

            if not empty_ok:
                return False

        #
        # 2. Rezerwacja przejazdu z zawieszką:
        #
        # source_station -> target_station
        #
        if (
            assignment.source_station
            != assignment.target_station
        ):
            loaded_ok = (
                self.track_service.can_reserve(
                    manipulator_id=(
                        manipulator.id
                    ),
                    source_station=(
                        assignment.source_station
                    ),
                    target_station=(
                        assignment.target_station
                    ),
                    start_time=(
                        assignment.transport_start_time
                    ),
                    travel_time_per_position=(
                        manipulator.travel_time_per_position
                    )
                )
            )

            if not loaded_ok:
                return False

        #
        # 3. Rezerwacja ruchu powrotnego / yield move:
        #
        # target_station -> return_position
        #
        if (
            assignment.return_position is not None
            and
            assignment.return_position
            != assignment.target_station
        ):
            return_ok = (
                self.track_service.can_reserve(
                    manipulator_id=(
                        manipulator.id
                    ),
                    source_station=(
                        assignment.target_station
                    ),
                    target_station=(
                        assignment.return_position
                    ),
                    start_time=(
                        assignment.return_start_time
                    ),
                    travel_time_per_position=(
                        manipulator.travel_time_per_position
                    )
                )
            )

            if not return_ok:
                return False

        return True

    def validate_order(
        self,
        manipulator,
        target_station: int,
        time_value: float | None = None
    ) -> bool:
        #
        # Zakaz mijania manipulatorów.
        #
        # Manipulator nie może planować celu:
        # - na lewo od lewego sąsiada,
        # - na prawo od prawego sąsiada.
        #
        if time_value is None:
            ordered = (
                self.manipulator_manager
                .sorted_by_position()
            )
        else:
            ordered = sorted(
                self.manipulator_manager.all(),
                key=lambda item:
                    self.position_at(
                        item,
                        time_value
                    )
            )

        index = next(
            idx
            for idx, item
            in enumerate(
                ordered
            )
            if item.id == manipulator.id
        )

        if index > 0:
            left = (
                ordered[
                    index
                    -
                    1
                ]
            )

            left_position = (
                self.position_at(
                    left,
                    time_value
                )
                if time_value is not None
                else left.position
            )

            left_gap = float(target_station) - float(left_position)
            if left_gap < float(self.minimum_manipulator_spacing):
                self.last_track_conflict = EventTrackConflict(
                    manipulator_id=int(manipulator.id),
                    neighbor_id=int(left.id),
                    conflict_start=float(time_value or 0.0),
                    conflict_end=float(time_value or 0.0),
                    minimum_gap=left_gap,
                    required_gap=float(self.minimum_manipulator_spacing),
                    side="left"
                )
                return False

        if (
            index
            <
            len(
                ordered
            )
            -
            1
        ):
            right = (
                ordered[
                    index
                    +
                    1
                ]
            )

            right_position = (
                self.position_at(
                    right,
                    time_value
                )
                if time_value is not None
                else right.position
            )

            right_gap = float(right_position) - float(target_station)
            if right_gap < float(self.minimum_manipulator_spacing):
                self.last_track_conflict = EventTrackConflict(
                    manipulator_id=int(manipulator.id),
                    neighbor_id=int(right.id),
                    conflict_start=float(time_value or 0.0),
                    conflict_end=float(time_value or 0.0),
                    minimum_gap=right_gap,
                    required_gap=float(self.minimum_manipulator_spacing),
                    side="right"
                )
                return False

        return True

    def validate_passing(
        self,
        manipulator,
        start_time,
        finish_time
    ):
        #
        # Na razie zostawiamy True.
        #
        # Faktyczny zakaz mijania jest realizowany przez validate_order().
        # Konflikty na torze są ograniczane przez:
        # - validate_assignment_track()
        # - validate_static_occupancy()
        # - track_service.can_reserve()
        #
        # Nie wracamy tutaj do minimum_manipulator_spacing, ponieważ
        # poprzednia implementacja blokowała legalny transport 6 -> 8
        # przez obecność M2 na pozycji 8.
        #
        return True