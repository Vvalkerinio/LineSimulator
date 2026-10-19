from src.model.program_consult import (
    ProgramConsult
)


class CollisionConsultGenerator:

    REASON_COLLISION = "COLLISION"

    WORD_STATION = "STATION"
    WORD_ACTION = "ACTION"
    WORD_WAIT = "WAIT"

    SEGMENT_IDLE = "idle"
    SEGMENT_EMPTY_MOVE = "empty_move"
    SEGMENT_LOADED_MOVE = "loaded_move"

    EPSILON = 1e-6

    def __init__(
        self,
        programs,
        simulation_result,
        configuration
    ):
        self.programs = (
            programs
            or
            {}
        )

        self.result = (
            simulation_result
        )

        self.configuration = (
            configuration
        )

    def generate(
        self
    ):
        collision = (
            self._first_actionable_collision()
        )

        if collision is None:
            return []

        consult = (
            self._consult_for_collision(
                collision
            )
        )

        if consult is None:
            print(
                "COLLISION CONSULT WARNING "
                "Nie udało się zbudować consulta dla kolizji: "
                f"{self._collision_to_text(collision)}"
            )

            return []

        print(
            "COLLISION CONSULT GENERATED "
            f"{consult.to_text()} "
            f"reason={consult.reason}"
        )

        return [
            consult
        ]

    def _minimum_spacing(
        self
    ):
        return float(
            getattr(
                self.configuration,
                "minimum_manipulator_spacing",
                1.0
            )
        )

    def _timeline_segments(
        self
    ):
        return list(
            getattr(
                self.result,
                "timeline_segments",
                []
            )
        )

    def _word_executions(
        self
    ):
        return list(
            getattr(
                self.result,
                "program_word_executions",
                []
            )
        )

    def _word_kind_name(
        self,
        word
    ):
        value = getattr(
            word,
            "word_kind",
            ""
        )

        name = getattr(
            value,
            "name",
            None
        )

        if name is not None:
            return str(
                name
            ).replace(
                "WORD_",
                ""
            )

        return str(
            value
        ).replace(
            "WORD_",
            ""
        )

    def _segment_type(
        self,
        segment
    ):
        return str(
            getattr(
                segment,
                "segment_type",
                ""
            )
        )

    def _segment_is_idle(
        self,
        segment
    ):
        return (
            self._segment_type(
                segment
            )
            ==
            self.SEGMENT_IDLE
        )

    def _segment_is_move(
        self,
        segment
    ):
        return (
            self._segment_type(
                segment
            )
            in [
                self.SEGMENT_EMPTY_MOVE,
                self.SEGMENT_LOADED_MOVE
            ]
        )

    def _segment_is_loaded(
        self,
        segment
    ):
        return (
            self._segment_type(
                segment
            )
            ==
            self.SEGMENT_LOADED_MOVE
        )

    def _position_at(
        self,
        segment,
        time_value
    ):
        start_time = float(
            segment.start_time
        )

        end_time = float(
            segment.end_time
        )

        start_position = float(
            segment.start_position
        )

        end_position = float(
            segment.end_position
        )

        if (
            end_time
            <=
            start_time
        ):
            return (
                end_position
            )

        ratio = (
            float(
                time_value
            )
            -
            start_time
        ) / (
            end_time
            -
            start_time
        )

        ratio = max(
            0.0,
            min(
                1.0,
                ratio
            )
        )

        return (
            start_position
            +
            (
                end_position
                -
                start_position
            )
            *
            ratio
        )

    def _velocity(
        self,
        segment
    ):
        start_time = float(
            segment.start_time
        )

        end_time = float(
            segment.end_time
        )

        if (
            end_time
            <=
            start_time
        ):
            return 0.0

        return (
            float(
                segment.end_position
            )
            -
            float(
                segment.start_position
            )
        ) / (
            end_time
            -
            start_time
        )

    def _segments_overlap_in_time(
        self,
        segment_a,
        segment_b
    ):
        return not (
            float(
                segment_a.end_time
            )
            <
            float(
                segment_b.start_time
            )
            or
            float(
                segment_b.end_time
            )
            <
            float(
                segment_a.start_time
            )
        )

    def _minimum_distance(
        self,
        segment_a,
        segment_b
    ):
        left = max(
            float(
                segment_a.start_time
            ),
            float(
                segment_b.start_time
            )
        )

        right = min(
            float(
                segment_a.end_time
            ),
            float(
                segment_b.end_time
            )
        )

        if (
            right
            <
            left
        ):
            return None

        check_times = [
            left,
            right,
            (
                left
                +
                right
            )
            /
            2.0
        ]

        velocity_a = (
            self._velocity(
                segment_a
            )
        )

        velocity_b = (
            self._velocity(
                segment_b
            )
        )

        relative_velocity = (
            velocity_a
            -
            velocity_b
        )

        if (
            abs(
                relative_velocity
            )
            >
            1e-9
        ):
            position_a_left = (
                self._position_at(
                    segment_a,
                    left
                )
            )

            position_b_left = (
                self._position_at(
                    segment_b,
                    left
                )
            )

            relative_position_left = (
                position_a_left
                -
                position_b_left
            )

            crossing_time = (
                left
                -
                relative_position_left
                /
                relative_velocity
            )

            if (
                left
                <=
                crossing_time
                <=
                right
            ):
                check_times.append(
                    crossing_time
                )

        best_distance = None
        best_time = None
        best_position_a = None
        best_position_b = None

        for time_value in check_times:
            position_a = (
                self._position_at(
                    segment_a,
                    time_value
                )
            )

            position_b = (
                self._position_at(
                    segment_b,
                    time_value
                )
            )

            distance = abs(
                position_a
                -
                position_b
            )

            if (
                best_distance is None
                or
                distance
                <
                best_distance
            ):
                best_distance = (
                    distance
                )

                best_time = (
                    time_value
                )

                best_position_a = (
                    position_a
                )

                best_position_b = (
                    position_b
                )

        return {
            "distance": best_distance,
            "time": best_time,
            "position_a": best_position_a,
            "position_b": best_position_b
        }

    def _first_actionable_collision(
        self
    ):
        segments = (
            self._timeline_segments()
        )

        spacing = (
            self._minimum_spacing()
        )

        first = None

        for index_a in range(
            len(
                segments
            )
        ):
            segment_a = (
                segments[
                    index_a
                ]
            )

            for index_b in range(
                index_a
                +
                1,
                len(
                    segments
                )
            ):
                segment_b = (
                    segments[
                        index_b
                    ]
                )

                if (
                    int(
                        segment_a.manipulator_id
                    )
                    ==
                    int(
                        segment_b.manipulator_id
                    )
                ):
                    continue

                if not self._segments_overlap_in_time(
                    segment_a,
                    segment_b
                ):
                    continue

                data = (
                    self._minimum_distance(
                        segment_a,
                        segment_b
                    )
                )

                if data is None:
                    continue

                if (
                    data[
                        "distance"
                    ]
                    >
                    spacing
                    +
                    self.EPSILON
                ):
                    continue

                collision = {
                    "time": float(
                        data[
                            "time"
                        ]
                    ),
                    "segment_a": segment_a,
                    "segment_b": segment_b,
                    "index_a": index_a,
                    "index_b": index_b,
                    "distance": float(
                        data[
                            "distance"
                        ]
                    ),
                    "position_a": float(
                        data[
                            "position_a"
                        ]
                    ),
                    "position_b": float(
                        data[
                            "position_b"
                        ]
                    ),
                    "spacing": float(
                        spacing
                    )
                }

                if not self._collision_is_actionable(
                    collision
                ):
                    continue

                if (
                    first is None
                    or
                    collision[
                        "time"
                    ]
                    <
                    first[
                        "time"
                    ]
                ):
                    first = (
                        collision
                    )

        if first is not None:
            print(
                "COLLISION CONSULT FIRST ACTIONABLE "
                f"{self._collision_to_text(first)}"
            )

        return first

    def _collision_is_actionable(
        self,
        collision
    ):
        segment_a = (
            collision[
                "segment_a"
            ]
        )

        segment_b = (
            collision[
                "segment_b"
            ]
        )

        a_idle = (
            self._segment_is_idle(
                segment_a
            )
        )

        b_idle = (
            self._segment_is_idle(
                segment_b
            )
        )

        a_move = (
            self._segment_is_move(
                segment_a
            )
        )

        b_move = (
            self._segment_is_move(
                segment_b
            )
        )

        #
        # Idle/idle z dystansem równym progowi jest tylko informacją,
        # że manipulatory są bardzo blisko. Nie da się tego sensownie
        # naprawić consultem na ruchu, bo żaden z nich nie wykonuje ruchu.
        #
        # Czekamy na pierwszy konflikt, gdzie co najmniej jeden manipulator
        # faktycznie wykonuje ruch.
        #
        if (
            a_idle
            and
            b_idle
        ):
            return False

        if (
            a_move
            or
            b_move
        ):
            return True

        return False

    def _collision_to_text(
        self,
        collision
    ):
        segment_a = (
            collision[
                "segment_a"
            ]
        )

        segment_b = (
            collision[
                "segment_b"
            ]
        )

        return (
            f"M{segment_a.manipulator_id}/"
            f"M{segment_b.manipulator_id} "
            f"t={collision['time']:.1f}s "
            f"pos={collision['position_a']:.2f}/"
            f"{collision['position_b']:.2f} "
            f"d={collision['distance']:.2f} "
            f"types={self._segment_type(segment_a)}/"
            f"{self._segment_type(segment_b)} "
            f"A={float(segment_a.start_time):.1f}"
            f"..{float(segment_a.end_time):.1f} "
            f"B={float(segment_b.start_time):.1f}"
            f"..{float(segment_b.end_time):.1f}"
        )

    def _choose_waiting_and_trigger_segments(
        self,
        collision
    ):
        segment_a = (
            collision[
                "segment_a"
            ]
        )

        segment_b = (
            collision[
                "segment_b"
            ]
        )

        a_idle = (
            self._segment_is_idle(
                segment_a
            )
        )

        b_idle = (
            self._segment_is_idle(
                segment_b
            )
        )

        a_move = (
            self._segment_is_move(
                segment_a
            )
        )

        b_move = (
            self._segment_is_move(
                segment_b
            )
        )

        #
        # Najważniejszy przypadek:
        # jeden manipulator stoi, drugi wjeżdża w jego odstęp.
        # Czeka ten, który wykonuje ruch.
        #
        if (
            a_move
            and
            b_idle
        ):
            return (
                segment_a,
                segment_b
            )

        if (
            b_move
            and
            a_idle
        ):
            return (
                segment_b,
                segment_a
            )

        #
        # Dwa ruchy:
        # 1. pusty ustępuje załadowanemu
        # 2. jeżeli obaj tak samo, ustępuje ten, który wystartował później
        # 3. przy remisie ustępuje wyższy numer manipulatora
        #
        if (
            a_move
            and
            b_move
        ):
            loaded_a = (
                self._segment_is_loaded(
                    segment_a
                )
            )

            loaded_b = (
                self._segment_is_loaded(
                    segment_b
                )
            )

            if (
                loaded_a
                and
                not loaded_b
            ):
                return (
                    segment_b,
                    segment_a
                )

            if (
                loaded_b
                and
                not loaded_a
            ):
                return (
                    segment_a,
                    segment_b
                )

            if (
                float(
                    segment_a.start_time
                )
                >
                float(
                    segment_b.start_time
                )
            ):
                return (
                    segment_a,
                    segment_b
                )

            if (
                float(
                    segment_b.start_time
                )
                >
                float(
                    segment_a.start_time
                )
            ):
                return (
                    segment_b,
                    segment_a
                )

            if (
                int(
                    segment_a.manipulator_id
                )
                >
                int(
                    segment_b.manipulator_id
                )
            ):
                return (
                    segment_a,
                    segment_b
                )

            return (
                segment_b,
                segment_a
            )

        return (
            None,
            None
        )

    def _words_for_manipulator(
        self,
        manipulator_id
    ):
        result = []

        for word in self._word_executions():
            if (
                int(
                    word.manipulator_id
                )
                !=
                int(
                    manipulator_id
                )
            ):
                continue

            result.append(
                word
            )

        result.sort(
            key=lambda word:
                (
                    int(
                        getattr(
                            word,
                            "cycle_no",
                            1
                        )
                    ),
                    float(
                        word.start_time
                    ),
                    int(
                        word.plc_index
                    )
                )
        )

        return result

    def _station_words_for_manipulator(
        self,
        manipulator_id
    ):
        return [
            word
            for word in self._words_for_manipulator(
                manipulator_id
            )
            if self._word_kind_name(
                word
            )
            ==
            self.WORD_STATION
        ]

    def _word_for_move_segment(
        self,
        segment
    ):
        candidates = []

        for word in self._station_words_for_manipulator(
            segment.manipulator_id
        ):
            start_distance = abs(
                float(
                    word.start_time
                )
                -
                float(
                    segment.start_time
                )
            )

            end_distance = abs(
                float(
                    word.end_time
                )
                -
                float(
                    segment.end_time
                )
            )

            position_distance = abs(
                float(
                    getattr(
                        word,
                        "start_position",
                        segment.start_position
                    )
                )
                -
                float(
                    segment.start_position
                )
            ) + abs(
                float(
                    getattr(
                        word,
                        "end_position",
                        segment.end_position
                    )
                )
                -
                float(
                    segment.end_position
                )
            )

            overlaps = not (
                float(
                    word.end_time
                )
                <
                float(
                    segment.start_time
                )
                or
                float(
                    word.start_time
                )
                >
                float(
                    segment.end_time
                )
            )

            target_match = abs(
                float(
                    getattr(
                        word,
                        "end_position",
                        segment.end_position
                    )
                )
                -
                float(
                    segment.end_position
                )
            )

            score = (
                position_distance
                *
                100.0
                +
                start_distance
                +
                end_distance
                +
                (
                    0.0
                    if overlaps
                    else 10000.0
                )
                +
                target_match
                *
                1000.0
            )

            candidates.append(
                (
                    score,
                    word
                )
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item:
                item[
                    0
                ]
        )

        return (
            candidates[
                0
            ][
                1
            ]
        )

    def _next_station_word_after_time(
        self,
        manipulator_id,
        time_value
    ):
        candidates = []

        for word in self._station_words_for_manipulator(
            manipulator_id
        ):
            if (
                float(
                    word.start_time
                )
                +
                self.EPSILON
                <
                float(
                    time_value
                )
            ):
                continue

            candidates.append(
                word
            )

        if candidates:
            candidates.sort(
                key=lambda word:
                    (
                        float(
                            word.start_time
                        ),
                        int(
                            word.plc_index
                        )
                    )
            )

            return candidates[
                0
            ]

        return None

    def _word_ending_after_time(
        self,
        manipulator_id,
        time_value
    ):
        candidates = []

        for word in self._words_for_manipulator(
            manipulator_id
        ):
            if (
                float(
                    word.end_time
                )
                +
                self.EPSILON
                <
                float(
                    time_value
                )
            ):
                continue

            candidates.append(
                word
            )

        if candidates:
            candidates.sort(
                key=lambda word:
                    (
                        float(
                            word.end_time
                        ),
                        int(
                            word.plc_index
                        )
                    )
            )

            return candidates[
                0
            ]

        return None

    def _clearance_word_for_trigger_segment(
        self,
        trigger_segment,
        collision_time
    ):
        #
        # Jeżeli trigger jest ruchem, wystarczy czekać aż jego ruch
        # stacyjny zostanie zakończony.
        #
        if self._segment_is_move(
            trigger_segment
        ):
            return self._word_for_move_segment(
                trigger_segment
            )

        #
        # Jeżeli trigger jest idle, oznacza to że manipulator stoi
        # w pozycji konfliktowej. Czekamy na pierwszy następny STATION
        # tego manipulatora, bo dopiero ten ruch fizycznie zwalnia miejsce.
        #
        if self._segment_is_idle(
            trigger_segment
        ):
            next_station_word = (
                self._next_station_word_after_time(
                    manipulator_id=(
                        trigger_segment.manipulator_id
                    ),
                    time_value=(
                        trigger_segment.end_time
                    )
                )
            )

            if next_station_word is not None:
                return next_station_word

            return self._word_ending_after_time(
                manipulator_id=(
                    trigger_segment.manipulator_id
                ),
                time_value=(
                    collision_time
                )
            )

        return self._word_ending_after_time(
            manipulator_id=(
                trigger_segment.manipulator_id
            ),
            time_value=(
                collision_time
            )
        )

    def _consult_for_collision(
        self,
        collision
    ):
        waiting_segment, trigger_segment = (
            self._choose_waiting_and_trigger_segments(
                collision
            )
        )

        if (
            waiting_segment is None
            or
            trigger_segment is None
        ):
            return None

        waiting_word = (
            self._word_for_move_segment(
                waiting_segment
            )
        )

        trigger_word = (
            self._clearance_word_for_trigger_segment(
                trigger_segment=(
                    trigger_segment
                ),
                collision_time=(
                    collision[
                        "time"
                    ]
                )
            )
        )

        if waiting_word is None:
            print(
                "COLLISION CONSULT WARNING "
                "Nie znaleziono source STATION word dla "
                f"M{waiting_segment.manipulator_id} "
                f"{self._segment_type(waiting_segment)} "
                f"{float(waiting_segment.start_time):.1f}"
                f"..{float(waiting_segment.end_time):.1f}"
            )

            return None

        if trigger_word is None:
            print(
                "COLLISION CONSULT WARNING "
                "Nie znaleziono target clearance word dla "
                f"M{trigger_segment.manipulator_id} "
                f"{self._segment_type(trigger_segment)} "
                f"{float(trigger_segment.start_time):.1f}"
                f"..{float(trigger_segment.end_time):.1f}"
            )

            return None

        if (
            int(
                waiting_word.manipulator_id
            )
            ==
            int(
                trigger_word.manipulator_id
            )
        ):
            return None

        waiting_program = (
            self.programs.get(
                int(
                    waiting_word.manipulator_id
                )
            )
        )

        trigger_program = (
            self.programs.get(
                int(
                    trigger_word.manipulator_id
                )
            )
        )

        if (
            waiting_program is None
            or
            trigger_program is None
        ):
            return None

        return ProgramConsult(
            source_manipulator_id=(
                int(
                    waiting_word.manipulator_id
                )
            ),
            source_logical_step_no=(
                int(
                    waiting_word.logical_step_no
                )
            ),
            source_plc_index=(
                int(
                    waiting_word.plc_index
                )
            ),
            source_word_address=(
                int(
                    waiting_word.word_address
                )
            ),
            target_manipulator_id=(
                int(
                    trigger_word.manipulator_id
                )
            ),
            target_logical_step_no=(
                int(
                    trigger_word.logical_step_no
                )
            ),
            target_plc_index=(
                int(
                    trigger_word.plc_index
                )
            ),
            target_word_address=(
                int(
                    trigger_word.word_address
                )
            ),
            source_cycle_time_start=(
                float(
                    waiting_word.start_time
                )
            ),
            source_cycle_time_end=(
                float(
                    waiting_word.end_time
                )
            ),
            target_cycle_time_start=(
                float(
                    trigger_word.start_time
                )
            ),
            target_cycle_time_end=(
                float(
                    trigger_word.end_time
                )
            ),
            reason=(
                self.REASON_COLLISION
            ),
            description=(
                f"Kolizja torowa: "
                f"{self._collision_to_text(collision)}. "
                f"M{waiting_word.manipulator_id} IDX "
                f"{waiting_word.plc_index} czeka, aż "
                f"M{trigger_word.manipulator_id} IDX "
                f"{trigger_word.plc_index} zwolni tor."
            )
        )