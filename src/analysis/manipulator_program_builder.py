from src.model.manipulator_program import (
    ManipulatorProgram
)

from src.model.manipulator_program_step import (
    ManipulatorProgramStep
)


class ManipulatorProgramBuilder:

    ACTION_PICKUP = 1
    ACTION_DROP = 2

    SEGMENT_PICKUP = "pickup"
    SEGMENT_DROP = "drop"
    SEGMENT_EMPTY_PARKING = "empty_parking"

    EVENT_EMPTY_SEGMENT_TYPES = {
        "empty_move",
        "empty_parking",
        "parking",
        "empty_parking_move"
    }

    TIME_TOLERANCE = 2.0

    def __init__(
        self,
        configuration,
        result,
        cycle_start_time,
        cycle_end_time,
        index_addresses_by_manipulator,
        station_offsets_by_manipulator=None,
        station_id_shift=1,
        max_program_words=99,
        minimum_wait_to_attach=0.1,
        enable_empty_parking=True,
        minimum_parking_gap=20.0,
        enable_event_driven_parking=True
    ):
        self.configuration = configuration
        self.result = result

        self.cycle_start_time = float(
            cycle_start_time
        )

        self.cycle_end_time = float(
            cycle_end_time
        )

        self.index_addresses_by_manipulator = (
            index_addresses_by_manipulator
            or
            {}
        )

        self.station_offsets_by_manipulator = (
            station_offsets_by_manipulator
            or
            {}
        )

        self.station_id_shift = int(
            station_id_shift
        )

        self.max_program_words = int(
            max_program_words
        )

        self.minimum_wait_to_attach = float(
            minimum_wait_to_attach
        )

        self.enable_empty_parking = bool(
            enable_empty_parking
        )

        self.minimum_parking_gap = float(
            minimum_parking_gap
        )

        self.enable_event_driven_parking = bool(
            enable_event_driven_parking
        )

    def _station_map(
        self
    ):
        return {
            station.id: station
            for station
            in getattr(
                self.configuration,
                "stations",
                []
            )
        }

    def _manipulator_map(
        self
    ):
        return {
            manipulator.id: manipulator
            for manipulator
            in getattr(
                self.configuration,
                "manipulators",
                []
            )
        }

    def _station_name(
        self,
        station_id
    ):
        if station_id is None:
            return ""

        station = (
            self._station_map()
            .get(
                int(
                    round(
                        station_id
                    )
                )
            )
        )

        if station is None:
            return ""

        return getattr(
            station,
            "name",
            ""
        )

    def _plc_station_value(
        self,
        manipulator_id,
        station_id
    ):
        station_offset = int(
            self.station_offsets_by_manipulator.get(
                manipulator_id,
                0
            )
        )

        return (
            int(
                round(
                    station_id
                )
            )
            +
            self.station_id_shift
            -
            station_offset
        )

    def _duration_to_01s(
        self,
        duration
    ):
        return int(
            round(
                max(
                    0.0,
                    float(
                        duration
                    )
                )
                *
                10.0
            )
        )

    def _cycle_time(
        self,
        time_value
    ):
        return (
            float(
                time_value
            )
            -
            self.cycle_start_time
        )

    def _lift_time_for(
        self,
        manipulator_id
    ):
        manipulator = (
            self._manipulator_map()
            .get(
                manipulator_id
            )
        )

        if manipulator is None:
            return 0.0

        return float(
            getattr(
                manipulator,
                "lift_time",
                0.0
            )
        )

    def _drop_time_for(
        self,
        manipulator_id
    ):
        manipulator = (
            self._manipulator_map()
            .get(
                manipulator_id
            )
        )

        if manipulator is None:
            return 0.0

        return float(
            getattr(
                manipulator,
                "drop_time",
                0.0
            )
        )

    def _drip_time_for_station(self, station_id):
        station = self._station_map().get(int(round(station_id)))
        if station is None:
            return 0.0
        return max(0.0, float(getattr(station, "drip_time", 0.0)))

    def _travel_time_for_manipulator(
        self,
        manipulator_id,
        source_station,
        target_station
    ):
        manipulator = (
            self._manipulator_map()
            .get(
                manipulator_id
            )
        )

        if manipulator is None:
            return 0.0

        return (
            abs(
                int(
                    round(
                        target_station
                    )
                )
                -
                int(
                    round(
                        source_station
                    )
                )
            )
            *
            float(
                manipulator.travel_time_per_position
            )
        )

    def _zone_range(
        self,
        manipulator
    ):
        start = int(
            getattr(
                manipulator,
                "work_zone_start",
                getattr(
                    manipulator,
                    "position",
                    1
                )
            )
        )

        end = int(
            getattr(
                manipulator,
                "work_zone_end",
                start
            )
        )

        if start > end:
            start, end = end, start

        return (
            start,
            end
        )

    def _path_crosses_foreign_zone(
        self,
        manipulator_id,
        source_station,
        target_station
    ):
        if (
            source_station is None
            or
            target_station is None
        ):
            return (
                False,
                None
            )

        source = int(
            round(
                source_station
            )
        )

        target = int(
            round(
                target_station
            )
        )

        path_start = min(
            source,
            target
        )

        path_end = max(
            source,
            target
        )

        for manipulator in getattr(
            self.configuration,
            "manipulators",
            []
        ):
            if (
                int(
                    manipulator.id
                )
                ==
                int(
                    manipulator_id
                )
            ):
                continue

            zone_start, zone_end = (
                self._zone_range(
                    manipulator
                )
            )

            if (
                path_start
                <=
                zone_end
                and
                path_end
                >=
                zone_start
            ):
                return (
                    True,
                    manipulator.id
                )

        return (
            False,
            None
        )

    def _new_step(
        self,
        manipulator_id,
        step_no,
        cycle_time_start,
        cycle_time_end,
        station_id,
        action,
        wait_time_01s,
        command_name,
        source_station=None,
        target_station=None,
        hanger_id=None,
        segment_type="",
        status="OK"
    ):
        station_id = int(
            round(
                station_id
            )
        )

        source = (
            int(
                round(
                    source_station
                )
            )
            if source_station is not None
            else None
        )

        target = (
            int(
                round(
                    target_station
                )
            )
            if target_station is not None
            else station_id
        )

        crosses = False
        foreign_owner = None

        if (
            source is not None
            and
            target is not None
            and
            source
            !=
            target
        ):
            crosses, foreign_owner = (
                self._path_crosses_foreign_zone(
                    manipulator_id=(
                        manipulator_id
                    ),
                    source_station=(
                        source
                    ),
                    target_station=(
                        target
                    )
                )
            )

        if crosses:
            status = (
                f"WEJSCIE_W_STREFE_M{foreign_owner}"
            )

        return ManipulatorProgramStep(
            manipulator_id=(
                int(
                    manipulator_id
                )
            ),
            step_no=(
                int(
                    step_no
                )
            ),
            cycle_time_start=(
                float(
                    cycle_time_start
                )
            ),
            cycle_time_end=(
                float(
                    cycle_time_end
                )
            ),
            station_id=(
                station_id
            ),
            plc_station_value=(
                self._plc_station_value(
                    manipulator_id,
                    station_id
                )
            ),
            action=(
                int(
                    action
                )
            ),
            wait_time_01s=(
                int(
                    wait_time_01s
                )
            ),
            command_name=(
                command_name
            ),
            station_name=(
                self._station_name(
                    station_id
                )
            ),
            source_station=(
                source
            ),
            target_station=(
                target
            ),
            source_name=(
                self._station_name(
                    source
                )
            ),
            target_name=(
                self._station_name(
                    target
                )
            ),
            hanger_id=(
                hanger_id
            ),
            segment_type=(
                segment_type
            ),
            crosses_foreign_zone=(
                crosses
            ),
            foreign_zone_owner=(
                foreign_owner
            ),
            status=(
                status
            )
        )

    def _is_empty_parking_step(
        self,
        step
    ):
        return (
            str(
                getattr(
                    step,
                    "segment_type",
                    ""
                )
            )
            ==
            self.SEGMENT_EMPTY_PARKING
        )

    def _is_material_step(
        self,
        step
    ):
        if self._is_empty_parking_step(
            step
        ):
            return False

        return (
            int(
                step.action
            )
            in [
                self.ACTION_PICKUP,
                self.ACTION_DROP
            ]
        )

    def _tasks_for_manipulator(
        self,
        manipulator_id
    ):
        tasks = []

        for task in getattr(
            self.result,
            "manipulator_tasks",
            []
        ):
            if (
                int(
                    task.manipulator_id
                )
                !=
                int(
                    manipulator_id
                )
            ):
                continue

            if (
                float(
                    task.start_time
                )
                <
                self.cycle_start_time
                -
                self.TIME_TOLERANCE
            ):
                continue

            if (
                float(
                    task.end_time
                )
                >
                self.cycle_end_time
                +
                self.TIME_TOLERANCE
            ):
                continue

            tasks.append(
                task
            )

        tasks.sort(
            key=lambda task:
                (
                    float(
                        task.start_time
                    ),
                    float(
                        task.end_time
                    ),
                    int(
                        task.hanger_id
                    )
                )
        )

        return tasks


    def _segment_type_name(
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

    def _segment_hanger_id(
        self,
        segment
    ):
        return getattr(
            segment,
            "hanger_id",
            None
        )

    def _positions_match(
        self,
        a,
        b
    ):
        return (
            int(
                round(
                    float(
                        a
                    )
                )
            )
            ==
            int(
                round(
                    float(
                        b
                    )
                )
            )
        )

    def _loaded_move_segment_for_task(
        self,
        task,
        manipulator_id
    ):
        source_station = int(
            round(
                task.source_station
            )
        )

        target_station = int(
            round(
                task.target_station
            )
        )

        task_start = float(
            task.start_time
        )

        task_end = float(
            task.end_time
        )

        task_hanger_id = getattr(
            task,
            "hanger_id",
            None
        )

        best_segment = None
        best_score = None

        for segment in getattr(
            self.result,
            "timeline_segments",
            []
        ):
            if (
                int(
                    segment.manipulator_id
                )
                !=
                int(
                    manipulator_id
                )
            ):
                continue

            segment_type = self._segment_type_name(
                segment
            )

            if (
                "loaded"
                not in segment_type
            ):
                continue

            if not self._positions_match(
                segment.start_position,
                source_station
            ):
                continue

            if not self._positions_match(
                segment.end_position,
                target_station
            ):
                continue

            segment_start = float(
                segment.start_time
            )

            segment_end = float(
                segment.end_time
            )

            if (
                segment_end
                <
                task_start
                -
                self.TIME_TOLERANCE
            ):
                continue

            if (
                segment_start
                >
                task_end
                +
                self.TIME_TOLERANCE
            ):
                continue

            score = (
                abs(
                    segment_start
                    -
                    task_start
                )
                +
                abs(
                    segment_end
                    -
                    task_end
                )
                *
                0.1
            )

            segment_hanger_id = self._segment_hanger_id(
                segment
            )

            if (
                task_hanger_id is not None
                and
                segment_hanger_id is not None
            ):
                try:
                    if (
                        int(
                            segment_hanger_id
                        )
                        !=
                        int(
                            task_hanger_id
                        )
                    ):
                        score += 10000.0
                except Exception:
                    score += 10000.0

            if (
                best_score is None
                or
                score
                <
                best_score
            ):
                best_score = score
                best_segment = segment

        return best_segment

    def _material_drop_time_for_task(
        self,
        task,
        manipulator_id
    ):
        #
        # Krytyczna poprawka:
        # task.end_time w EventDriven może oznaczać ASSIGN finish,
        # czyli koniec całego zadania manipulatora po pustym odjeździe.
        #
        # Rzeczywisty materialny DROP bierzemy z końca loaded_move.
        #
        segment = self._loaded_move_segment_for_task(
            task=(
                task
            ),
            manipulator_id=(
                manipulator_id
            )
        )

        if segment is not None:
            return float(
                segment.end_time
            )

        return float(
            task.end_time
        )

    def _event_position_at(
        self,
        manipulator_id,
        time_value
    ):
        time_value = float(
            time_value
        )

        best_previous = None

        for segment in getattr(
            self.result,
            "timeline_segments",
            []
        ):
            if (
                int(
                    segment.manipulator_id
                )
                !=
                int(
                    manipulator_id
                )
            ):
                continue

            segment_start = float(
                segment.start_time
            )

            segment_end = float(
                segment.end_time
            )

            if (
                segment_start
                <=
                time_value
                <=
                segment_end
            ):
                if (
                    segment_end
                    <=
                    segment_start
                ):
                    return float(
                        segment.end_position
                    )

                ratio = (
                    time_value
                    -
                    segment_start
                ) / (
                    segment_end
                    -
                    segment_start
                )

                ratio = max(
                    0.0,
                    min(
                        1.0,
                        ratio
                    )
                )

                return (
                    float(
                        segment.start_position
                    )
                    +
                    (
                        float(
                            segment.end_position
                        )
                        -
                        float(
                            segment.start_position
                        )
                    )
                    *
                    ratio
                )

            if (
                segment_end
                <=
                time_value
            ):
                if (
                    best_previous is None
                    or
                    segment_end
                    >
                    float(
                        best_previous.end_time
                    )
                ):
                    best_previous = segment

        if best_previous is not None:
            return float(
                best_previous.end_position
            )

        manipulator = (
            self._manipulator_map().get(
                manipulator_id
            )
        )

        if manipulator is None:
            return 0.0

        return float(
            getattr(
                manipulator,
                "position",
                0.0
            )
        )

    def _infer_parking_position_from_event_driven_gap(
        self,
        manipulator_id,
        gap_start_time,
        gap_end_time,
        drop_station,
        next_source_station
    ):
        gap_start_time = float(
            gap_start_time
        )

        gap_end_time = float(
            gap_end_time
        )

        if (
            gap_end_time
            <=
            gap_start_time
            +
            self.TIME_TOLERANCE
        ):
            return None

        sample_times = [
            gap_start_time
            +
            (
                gap_end_time
                -
                gap_start_time
            )
            *
            0.20,
            gap_start_time
            +
            (
                gap_end_time
                -
                gap_start_time
            )
            *
            0.35,
            gap_start_time
            +
            (
                gap_end_time
                -
                gap_start_time
            )
            *
            0.50,
            gap_start_time
            +
            (
                gap_end_time
                -
                gap_start_time
            )
            *
            0.65,
            gap_start_time
            +
            (
                gap_end_time
                -
                gap_start_time
            )
            *
            0.80
        ]

        counts = {}

        for sample_time in sample_times:
            position = int(
                round(
                    self._event_position_at(
                        manipulator_id,
                        sample_time
                    )
                )
            )

            counts[
                position
            ] = (
                counts.get(
                    position,
                    0
                )
                +
                1
            )

        if not counts:
            return None

        ranked = sorted(
            counts.items(),
            key=lambda item:
                (
                    -item[
                        1
                    ],
                    item[
                        0
                    ]
                )
        )

        drop_station = int(
            round(
                drop_station
            )
        )

        next_source = (
            int(
                round(
                    next_source_station
                )
            )
            if next_source_station is not None
            else None
        )

        for position, _count in ranked:
            if position == drop_station:
                continue

            if (
                next_source is not None
                and
                position
                ==
                next_source
            ):
                continue

            return position

        return None

    def _append_inferred_event_parking(
        self,
        program,
        steps,
        manipulator_id,
        gap_start_time,
        gap_end_time,
        drop_station,
        next_source_station
    ):
        target_station = (
            self._infer_parking_position_from_event_driven_gap(
                manipulator_id=(
                    manipulator_id
                ),
                gap_start_time=(
                    gap_start_time
                ),
                gap_end_time=(
                    gap_end_time
                ),
                drop_station=(
                    drop_station
                ),
                next_source_station=(
                    next_source_station
                )
            )
        )

        if target_station is None:
            return 0

        source_station = int(
            round(
                drop_station
            )
        )

        target_station = int(
            round(
                target_station
            )
        )

        if target_station == source_station:
            return 0

        if (
            len(
                steps
            )
            >=
            program.max_logical_steps()
        ):
            program.warnings.append(
                (
                    f"M{manipulator_id}: brak miejsca na inferowany "
                    f"parking EventDriven S{source_station}->"
                    f"S{target_station}."
                )
            )

            return 0

        travel_time = (
            self._travel_time_for_manipulator(
                manipulator_id,
                source_station,
                target_station
            )
        )

        arrival_absolute_time = min(
            float(
                gap_end_time
            ),
            float(
                gap_start_time
            )
            +
            travel_time
        )

        steps.append(
            self._new_step(
                manipulator_id=(
                    manipulator_id
                ),
                step_no=(
                    0
                ),
                cycle_time_start=(
                    self._cycle_time(
                        arrival_absolute_time
                    )
                ),
                cycle_time_end=(
                    self._cycle_time(
                        arrival_absolute_time
                    )
                ),
                station_id=(
                    target_station
                ),
                action=(
                    self.ACTION_DROP
                ),
                wait_time_01s=(
                    0
                ),
                command_name=(
                    "PARK_EMPTY"
                ),
                source_station=(
                    source_station
                ),
                target_station=(
                    target_station
                ),
                hanger_id=(
                    None
                ),
                segment_type=(
                    self.SEGMENT_EMPTY_PARKING
                ),
                status=(
                    "EVENT_DRIVEN_PARKING_INFERRED"
                )
            )
        )

        program.warnings.append(
            (
                f"Zinferowano parking EventDriven M{manipulator_id}: "
                f"S{source_station}->S{target_station}, "
                f"gap={float(gap_start_time):.1f}"
                f"..{float(gap_end_time):.1f}. "
                f"Pozycja w luce wskazuje parking mimo braku "
                f"jawnego empty_move."
            )
        )

        return 1


    def _append_task_steps(
        self,
        steps,
        manipulator_id,
        task
    ):
        source = int(
            round(
                task.source_station
            )
        )

        target = int(
            round(
                task.target_station
            )
        )

        lift_time = (
            self._lift_time_for(
                manipulator_id
            )
        )

        drop_time = (
            self._drop_time_for(
                manipulator_id
            )
        )

        pickup_start = float(
            task.start_time
        )

        pickup_end = (
            pickup_start
            +
            lift_time
        )

        material_drop_time = (
            self._material_drop_time_for_task(
                task=(
                    task
                ),
                manipulator_id=(
                    manipulator_id
                )
            )
        )

        drop_end = float(
            material_drop_time
        )

        drop_start = max(
            pickup_end,
            drop_end
            -
            drop_time
        )

        steps.append(
            self._new_step(
                manipulator_id=(
                    manipulator_id
                ),
                step_no=(
                    0
                ),
                cycle_time_start=(
                    self._cycle_time(
                        pickup_start
                    )
                ),
                cycle_time_end=(
                    self._cycle_time(
                        pickup_end
                    )
                ),
                station_id=(
                    source
                ),
                action=(
                    self.ACTION_PICKUP
                ),
                wait_time_01s=(
                    self._duration_to_01s(
                        self._drip_time_for_station(source)
                    )
                ),
                command_name=(
                    "PODNIES"
                ),
                source_station=(
                    source
                ),
                target_station=(
                    source
                ),
                hanger_id=(
                    task.hanger_id
                ),
                segment_type=(
                    self.SEGMENT_PICKUP
                ),
                status=(
                    "MATERIAL_PICKUP"
                )
            )
        )

        steps.append(
            self._new_step(
                manipulator_id=(
                    manipulator_id
                ),
                step_no=(
                    0
                ),
                cycle_time_start=(
                    self._cycle_time(
                        drop_start
                    )
                ),
                cycle_time_end=(
                    self._cycle_time(
                        drop_end
                    )
                ),
                station_id=(
                    target
                ),
                action=(
                    self.ACTION_DROP
                ),
                wait_time_01s=(
                    0
                ),
                command_name=(
                    "OPUSC"
                ),
                source_station=(
                    source
                ),
                target_station=(
                    target
                ),
                hanger_id=(
                    task.hanger_id
                ),
                segment_type=(
                    self.SEGMENT_DROP
                ),
                status=(
                    "MATERIAL_DROP"
                )
            )
        )

    def _is_empty_event_segment(
        self,
        segment
    ):
        segment_type = str(
            getattr(
                segment,
                "segment_type",
                ""
            )
        )

        if (
            segment_type
            not in self.EVENT_EMPTY_SEGMENT_TYPES
        ):
            return False

        if (
            getattr(
                segment,
                "hanger_id",
                None
            )
            is not None
        ):
            return False

        source = int(
            round(
                segment.start_position
            )
        )

        target = int(
            round(
                segment.end_position
            )
        )

        if source == target:
            return False

        if (
            float(
                segment.end_time
            )
            <=
            float(
                segment.start_time
            )
        ):
            return False

        return True

    def _empty_event_segments_between(
        self,
        manipulator_id,
        start_time,
        end_time
    ):
        segments = []

        for segment in getattr(
            self.result,
            "timeline_segments",
            []
        ):
            if (
                int(
                    segment.manipulator_id
                )
                !=
                int(
                    manipulator_id
                )
            ):
                continue

            if not self._is_empty_event_segment(
                segment
            ):
                continue

            if (
                float(
                    segment.start_time
                )
                <
                float(
                    start_time
                )
                -
                self.TIME_TOLERANCE
            ):
                continue

            if (
                float(
                    segment.end_time
                )
                >
                float(
                    end_time
                )
                +
                self.TIME_TOLERANCE
            ):
                continue

            segments.append(
                segment
            )

        segments.sort(
            key=lambda segment:
                (
                    float(
                        segment.start_time
                    ),
                    float(
                        segment.end_time
                    ),
                    int(
                        round(
                            segment.start_position
                        )
                    ),
                    int(
                        round(
                            segment.end_position
                        )
                    )
                )
        )

        return segments


    def _append_event_parking_after_task(
        self,
        program,
        steps,
        manipulator_id,
        gap_start_time,
        gap_end_time,
        next_source_station,
        drop_station
    ):
        if not self.enable_event_driven_parking:
            return 0

        empty_segments = (
            self._empty_event_segments_between(
                manipulator_id=(
                    manipulator_id
                ),
                start_time=(
                    gap_start_time
                ),
                end_time=(
                    gap_end_time
                )
            )
        )

        inserted = 0
        final_approach_skipped = 0

        for index, segment in enumerate(
            empty_segments
        ):
            source = int(
                round(
                    segment.start_position
                )
            )

            target = int(
                round(
                    segment.end_position
                )
            )

            is_last_empty_segment = (
                index
                ==
                len(
                    empty_segments
                )
                -
                1
            )

            is_final_approach_to_next_pickup = (
                next_source_station is not None
                and
                is_last_empty_segment
                and
                target
                ==
                int(
                    round(
                        next_source_station
                    )
                )
            )

            if is_final_approach_to_next_pickup:
                final_approach_skipped += 1

                program.warnings.append(
                    (
                        f"Pominięto dojazd do następnego PICKUP "
                        f"M{manipulator_id}: "
                        f"S{source}->S{target}, "
                        f"t={float(segment.start_time):.1f}"
                        f"..{float(segment.end_time):.1f}. "
                        f"Ten ruch wykona krok PODNIES."
                    )
                )
                continue

            if (
                len(
                    steps
                )
                >=
                program.max_logical_steps()
            ):
                program.warnings.append(
                    (
                        f"M{manipulator_id}: brak miejsca na parking "
                        f"EventDriven S{source}->S{target}. "
                        f"Limit={program.max_logical_steps()}."
                    )
                )
                break

            arrival_cycle_time = (
                self._cycle_time(
                    float(
                        segment.end_time
                    )
                )
            )

            steps.append(
                self._new_step(
                    manipulator_id=(
                        manipulator_id
                    ),
                    step_no=(
                        0
                    ),
                    cycle_time_start=(
                        arrival_cycle_time
                    ),
                    cycle_time_end=(
                        arrival_cycle_time
                    ),
                    station_id=(
                        target
                    ),
                    action=(
                        self.ACTION_DROP
                    ),
                    wait_time_01s=(
                        0
                    ),
                    command_name=(
                        "PARK_EMPTY"
                    ),
                    source_station=(
                        source
                    ),
                    target_station=(
                        target
                    ),
                    hanger_id=(
                        None
                    ),
                    segment_type=(
                        self.SEGMENT_EMPTY_PARKING
                    ),
                    status=(
                        "EVENT_DRIVEN_PARKING"
                    )
                )
            )

            inserted += 1

            program.warnings.append(
                (
                    f"Dodano parking EventDriven M{manipulator_id}: "
                    f"S{source}->S{target}, "
                    f"type={getattr(segment, 'segment_type', '')}, "
                    f"t={float(segment.start_time):.1f}"
                    f"..{float(segment.end_time):.1f}."
                )
            )

        if inserted > 0:
            return inserted

        #
        # Jeśli były tylko finalne dojazdy do next PICKUP albo nie było
        # jawnych empty segmentów, próbujemy odtworzyć parking z pozycji
        # manipulatora w luce.
        #
        inferred = (
            self._append_inferred_event_parking(
                program=(
                    program
                ),
                steps=(
                    steps
                ),
                manipulator_id=(
                    manipulator_id
                ),
                gap_start_time=(
                    gap_start_time
                ),
                gap_end_time=(
                    gap_end_time
                ),
                drop_station=(
                    drop_station
                ),
                next_source_station=(
                    next_source_station
                )
            )
        )

        if inferred > 0:
            return inferred

        if not empty_segments:
            program.warnings.append(
                (
                    f"M{manipulator_id}: brak pustych segmentów "
                    f"EventDriven w luce {gap_start_time:.1f}"
                    f"..{gap_end_time:.1f} i nie udało się "
                    f"zainferować parkingu z pozycji manipulatora."
                )
            )

        elif final_approach_skipped > 0:
            program.warnings.append(
                (
                    f"M{manipulator_id}: w luce {gap_start_time:.1f}"
                    f"..{gap_end_time:.1f} znaleziono tylko dojazd "
                    f"do następnego PICKUP, bez osobnego parkingu."
                )
            )

        return 0

    def _attach_waits_to_match_next_departure(
        self,
        program,
        steps,
        manipulator_id
    ):
        if len(
            steps
        ) < 2:
            return

        for index in range(
            len(
                steps
            )
            -
            1
        ):
            current = (
                steps[
                    index
                ]
            )

            next_step = (
                steps[
                    index
                    +
                    1
                ]
            )

            current_station = int(
                round(
                    current.station_id
                )
            )

            next_station = int(
                round(
                    next_step.station_id
                )
            )

            travel_to_next = (
                self._travel_time_for_manipulator(
                    manipulator_id,
                    current_station,
                    next_station
                )
            )

            desired_departure = (
                float(
                    next_step.cycle_time_start
                )
                -
                travel_to_next
            )

            gap = (
                desired_departure
                -
                float(
                    current.cycle_time_end
                )
            )

            if (
                gap
                <=
                self.minimum_wait_to_attach
            ):
                continue

            # WAIT po ACTION_PICKUP ma jednoznaczne znaczenie:
            # jest to wyłącznie czas ocieku skonfigurowany dla wanny.
            # Nie wolno dopisywać tutaj luki odtwarzającej fazę cyklu,
            # ponieważ manipulator trzymałby detal w górze dłużej niż
            # ustawiony czas ocieku. Taką synchronizację powinny
            # realizować consulty / planowanie toru, a nie WAIT pickup.
            if int(current.action) == self.ACTION_PICKUP:
                program.warnings.append(
                    (
                        f"M{manipulator_id}: pominięto dodatkowy WAIT "
                        f"{gap:.1f}s po PODNIES na S{current_station}; "
                        f"pozostawiono ociek "
                        f"{current.wait_time_01s / 10.0:.1f}s."
                    )
                )
                continue

            current.wait_time_01s += (
                self._duration_to_01s(
                    gap
                )
            )


    def _prepend_cycle_start_hold(self, program, steps, manipulator_id):
        if not steps:
            return
        first_step = min(steps, key=lambda item: float(item.cycle_time_start))
        start_position = int(round(self._event_position_at(
            manipulator_id,
            self.cycle_start_time
        )))
        travel_time = self._travel_time_for_manipulator(
            manipulator_id,
            start_position,
            int(first_step.station_id)
        )
        departure_time = max(0.0, float(first_step.cycle_time_start) - travel_time)
        steps.append(self._new_step(
            manipulator_id=manipulator_id,
            step_no=0,
            cycle_time_start=0.0,
            cycle_time_end=0.0,
            station_id=start_position,
            action=self.ACTION_DROP,
            wait_time_01s=self._duration_to_01s(departure_time),
            command_name="POSTOJ_START",
            source_station=start_position,
            target_station=start_position,
            hanger_id=None,
            segment_type=self.SEGMENT_EMPTY_PARKING,
            status="CYCLE_START_HOLD"
        ))

    def _build_for_manipulator(
        self,
        manipulator_id
    ):
        index_address = int(
            self.index_addresses_by_manipulator.get(
                manipulator_id,
                0
            )
        )

        station_offset = int(
            self.station_offsets_by_manipulator.get(
                manipulator_id,
                0
            )
        )

        program = ManipulatorProgram(
            manipulator_id=(
                manipulator_id
            ),
            index_address=(
                index_address
            ),
            station_offset=(
                station_offset
            ),
            station_id_shift=(
                self.station_id_shift
            ),
            max_program_words=(
                self.max_program_words
            )
        )

        steps = []

        tasks = (
            self._tasks_for_manipulator(
                manipulator_id
            )
        )

        if not tasks:
            program.steps = []
            return program

        for task_index, task in enumerate(
            tasks
        ):
            self._append_task_steps(
                steps=(
                    steps
                ),
                manipulator_id=(
                    manipulator_id
                ),
                task=(
                    task
                )
            )

            material_drop_time = (
                self._material_drop_time_for_task(
                    task=(
                        task
                    ),
                    manipulator_id=(
                        manipulator_id
                    )
                )
            )

            gap_start_time = float(
                material_drop_time
            )

            current_drop_station = int(
                round(
                    task.target_station
                )
            )

            if (
                task_index
                <
                len(
                    tasks
                )
                -
                1
            ):
                next_task = (
                    tasks[
                        task_index
                        +
                        1
                    ]
                )

                gap_end_time = float(
                    next_task.start_time
                )

                next_source_station = int(
                    round(
                        next_task.source_station
                    )
                )

            else:
                gap_end_time = (
                    self.cycle_end_time
                )

                next_source_station = None

            if (
                gap_end_time
                >
                gap_start_time
            ):
                self._append_event_parking_after_task(
                    program=(
                        program
                    ),
                    steps=(
                        steps
                    ),
                    manipulator_id=(
                        manipulator_id
                    ),
                    gap_start_time=(
                        gap_start_time
                    ),
                    gap_end_time=(
                        gap_end_time
                    ),
                    next_source_station=(
                        next_source_station
                    ),
                    drop_station=(
                        current_drop_station
                    )
                )

        self._prepend_cycle_start_hold(
            program,
            steps,
            manipulator_id
        )

        steps.sort(
            key=lambda step:
                (
                    float(
                        step.cycle_time_start
                    ),
                    0
                    if self._is_empty_parking_step(
                        step
                    )
                    else 1,
                    int(
                        step.action
                    ),
                    int(
                        step.station_id
                    )
                )
        )

        self._attach_waits_to_match_next_departure(
            program=(
                program
            ),
            steps=(
                steps
            ),
            manipulator_id=(
                manipulator_id
            )
        )

        for index, step in enumerate(
            steps,
            start=1
        ):
            step.step_no = index

        program.steps = steps

        if (
            len(
                steps
            )
            >
            program.max_logical_steps()
        ):
            program.warnings.append(
                (
                    f"M{manipulator_id}: "
                    f"{len(steps)} krokow PLC, "
                    f"limit={program.max_logical_steps()}."
                )
            )

        return program

    def _renumber_program_steps(
        self,
        programs
    ):
        for program in programs.values():
            for index, step in enumerate(
                program.steps,
                start=1
            ):
                step.step_no = index

    def build(
        self
    ):
        programs = {}

        manipulator_ids = sorted(
            {
                manipulator.id
                for manipulator
                in getattr(
                    self.configuration,
                    "manipulators",
                    []
                )
            }
        )

        for manipulator_id in manipulator_ids:
            programs[
                manipulator_id
            ] = (
                self._build_for_manipulator(
                    manipulator_id
                )
            )

        self._renumber_program_steps(
            programs
        )

        return programs