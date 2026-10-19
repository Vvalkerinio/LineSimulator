from copy import copy

from bisect import (
    bisect_left,
    bisect_right
)

from src.model.material_cycle_candidate import (
    MaterialCycleCandidate
)


class MaterialCycleWindowFinder:

    ACTION_PICKUP = "PICKUP"
    ACTION_DROP = "DROP"

    SEGMENT_IDLE = "idle"
    SEGMENT_EMPTY_MOVE = "empty_move"
    SEGMENT_LOADED_MOVE = "loaded_move"

    EMPTY_SEGMENT_TYPES = {
        "empty_move",
        "empty_parking",
        "parking",
        "empty_parking_move"
    }

    MATERIAL_SEGMENT_TYPES = {
        "loaded_move"
    }

    TIME_TOLERANCE = 1e-3

    def __init__(
        self,
        configuration,
        result,
        max_program_words=99
    ):
        self.configuration = configuration
        self.result = result

        self.max_program_words = int(
            max_program_words
        )

        self.max_logical_steps = (
            self.max_program_words
            //
            3
        )

        self._tasks_by_hanger_cache = None
        self._station_intervals_cache = None
        self._all_tasks_cache = None
        self._all_segments_cache = None
        self._segments_by_manipulator_cache = None
        self._occupancy_signature_cache = {}
        self._manipulator_signature_cache = {}
        self._boundary_errors_cache = {}
        self._transport_signature_cache = {}
        self._trajectory_signature_cache = {}
        self._tasks_window_cache = {}
        self._segments_window_cache = {}
        self._candidate_cache = {}
        self._candidate_cache_hits = 0
        self._candidate_cache_misses = 0

    def _enabled_route(
        self
    ):
        route = []
        processed_groups = set()

        for station in getattr(
            self.configuration,
            "stations",
            []
        ):
            if not getattr(
                station,
                "enabled",
                True
            ):
                continue

            group = getattr(
                station,
                "shared_bath_group",
                None
            )

            if (
                group is None
                or str(
                    group
                ).strip()
                ==
                ""
                or str(
                    group
                ).strip().lower()
                ==
                "none"
            ):
                route.append(
                    int(
                        station.id
                    )
                )
                continue

            group = str(
                group
            ).strip()

            if group in processed_groups:
                continue

            processed_groups.add(
                group
            )

            route.append(
                int(
                    station.id
                )
            )

        return route

    def _load_unload_stations(
        self
    ):
        route = (
            self._enabled_route()
        )

        if not route:
            return (
                None,
                None
            )

        return (
            route[
                0
            ],
            route[
                -1
            ]
        )

    def _station_capacity_groups(
        self
    ):
        capacities = {}
        grouped_stations = {}

        for station in getattr(
            self.configuration,
            "stations",
            []
        ):
            if not getattr(
                station,
                "enabled",
                True
            ):
                continue

            station_id = int(
                station.id
            )

            group = getattr(
                station,
                "shared_bath_group",
                None
            )

            if (
                group is None
                or str(
                    group
                ).strip()
                ==
                ""
                or str(
                    group
                ).strip().lower()
                ==
                "none"
            ):
                key = (
                    "station",
                    station_id
                )

            else:
                key = (
                    "group",
                    str(
                        group
                    ).strip()
                )

            if key not in grouped_stations:
                grouped_stations[
                    key
                ] = []

            grouped_stations[
                key
            ].append(
                station
            )

        for key, stations in grouped_stations.items():
            min_times = [
                float(
                    getattr(
                        station,
                        "min_process_time",
                        0.0
                    )
                )
                for station
                in stations
                if float(
                    getattr(
                        station,
                        "min_process_time",
                        0.0
                    )
                )
                >
                0.0
            ]

            if not min_times:
                continue

            capacity = len(
                stations
            )

            min_time = min(
                min_times
            )

            for station in stations:
                capacities[
                    int(
                        station.id
                    )
                ] = {
                    "key": key,
                    "capacity": capacity,
                    "min_time": min_time
                }

        return capacities

    def _configured_manipulator_positions(
        self
    ):
        result = {}

        for manipulator in getattr(
            self.configuration,
            "manipulators",
            []
        ):
            result[
                int(
                    manipulator.id
                )
            ] = int(
                round(
                    getattr(
                        manipulator,
                        "position",
                        0
                    )
                )
            )

        return result

    def _manipulator_ids(
        self
    ):
        ids = set()

        for manipulator in getattr(
            self.configuration,
            "manipulators",
            []
        ):
            ids.add(
                int(
                    manipulator.id
                )
            )

        for task in self._all_tasks():
            ids.add(
                int(
                    task.manipulator_id
                )
            )

        for segment in self._all_segments():
            ids.add(
                int(
                    segment.manipulator_id
                )
            )

        return sorted(
            ids
        )

    def _all_tasks(
        self
    ):
        if self._all_tasks_cache is not None:
            return self._all_tasks_cache

        tasks = list(
            getattr(
                self.result,
                "manipulator_tasks",
                []
            )
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
                        task.manipulator_id
                    ),
                    int(
                        task.hanger_id
                    ),
                    int(
                        task.source_station
                    ),
                    int(
                        task.target_station
                    )
                )
        )

        self._all_tasks_cache = tasks

        return tasks

    def _all_segments(
        self
    ):
        if self._all_segments_cache is not None:
            return self._all_segments_cache

        segments = list(
            getattr(
                self.result,
                "timeline_segments",
                []
            )
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
                        segment.manipulator_id
                    ),
                    float(
                        segment.start_position
                    ),
                    float(
                        segment.end_position
                    )
                )
        )

        self._all_segments_cache = segments

        return segments

    def _segments_by_manipulator(
        self
    ):
        if self._segments_by_manipulator_cache is not None:
            return self._segments_by_manipulator_cache

        result = {}

        for segment in self._all_segments():
            manipulator_id = int(
                segment.manipulator_id
            )

            if manipulator_id not in result:
                result[
                    manipulator_id
                ] = []

            result[
                manipulator_id
            ].append(
                segment
            )

        self._segments_by_manipulator_cache = result

        return result

    def _tasks_in_window(
        self,
        start_time,
        end_time
    ):
        key = (
            round(
                float(
                    start_time
                ),
                3
            ),
            round(
                float(
                    end_time
                ),
                3
            )
        )

        if key in self._tasks_window_cache:
            return self._tasks_window_cache[
                key
            ]

        tasks = []

        for task in self._all_tasks():
            if (
                float(
                    task.start_time
                )
                >=
                float(
                    start_time
                )
                -
                self.TIME_TOLERANCE
                and
                float(
                    task.end_time
                )
                <=
                float(
                    end_time
                )
                +
                self.TIME_TOLERANCE
            ):
                tasks.append(
                    task
                )

        self._tasks_window_cache[
            key
        ] = tasks

        return tasks

    def _segments_in_window(
        self,
        start_time,
        end_time
    ):
        key = (
            round(
                float(
                    start_time
                ),
                3
            ),
            round(
                float(
                    end_time
                ),
                3
            )
        )

        if key in self._segments_window_cache:
            return self._segments_window_cache[
                key
            ]

        segments = []

        for segment in self._all_segments():
            if (
                float(
                    segment.start_time
                )
                >=
                float(
                    start_time
                )
                -
                self.TIME_TOLERANCE
                and
                float(
                    segment.end_time
                )
                <=
                float(
                    end_time
                )
                +
                self.TIME_TOLERANCE
            ):
                segments.append(
                    segment
                )

        self._segments_window_cache[
            key
        ] = segments

        return segments

    def _tasks_by_hanger(
        self
    ):
        if self._tasks_by_hanger_cache is not None:
            return self._tasks_by_hanger_cache

        result = {}

        for task in self._all_tasks():
            hanger_id = int(
                task.hanger_id
            )

            if hanger_id not in result:
                result[
                    hanger_id
                ] = []

            result[
                hanger_id
            ].append(
                task
            )

        for hanger_id in result:
            result[
                hanger_id
            ].sort(
                key=lambda task:
                    (
                        float(
                            task.start_time
                        ),
                        float(
                            task.end_time
                        )
                    )
            )

        self._tasks_by_hanger_cache = result

        return result

    def _station_intervals(
        self
    ):
        if self._station_intervals_cache is not None:
            return self._station_intervals_cache

        _load_station, unload_station = (
            self._load_unload_stations()
        )

        intervals = []

        final_time = float(
            getattr(
                self.result,
                "final_time",
                0.0
            )
        )

        for hanger_id, tasks in self._tasks_by_hanger().items():
            for index, task in enumerate(
                tasks
            ):
                target_station = int(
                    task.target_station
                )

                if (
                    target_station
                    ==
                    unload_station
                ):
                    continue

                drop_time = float(
                    task.end_time
                )

                next_pickup_time = None

                for next_task in tasks[
                    index
                    +
                    1:
                ]:
                    if (
                        int(
                            next_task.source_station
                        )
                        ==
                        target_station
                    ):
                        next_pickup_time = float(
                            next_task.start_time
                        )
                        break

                if next_pickup_time is None:
                    next_pickup_time = final_time

                if (
                    next_pickup_time
                    <=
                    drop_time
                ):
                    continue

                intervals.append(
                    {
                        "hanger_id": int(
                            hanger_id
                        ),
                        "station_id": int(
                            target_station
                        ),
                        "start_time": drop_time,
                        "end_time": next_pickup_time
                    }
                )

        self._station_intervals_cache = intervals

        return intervals

    def _occupancy_signature_at(
        self,
        time_value
    ):
        key = round(
            float(
                time_value
            ),
            3
        )

        if key in self._occupancy_signature_cache:
            return self._occupancy_signature_cache[
                key
            ]

        counts = {}

        for interval in self._station_intervals():
            if (
                float(
                    interval[
                        "start_time"
                    ]
                )
                <=
                key
                <
                float(
                    interval[
                        "end_time"
                    ]
                )
            ):
                station_id = int(
                    interval[
                        "station_id"
                    ]
                )

                counts[
                    station_id
                ] = (
                    counts.get(
                        station_id,
                        0
                    )
                    +
                    1
                )

        signature = tuple(
            sorted(
                (
                    station_id,
                    count
                )
                for station_id, count
                in counts.items()
                if count != 0
            )
        )

        self._occupancy_signature_cache[
            key
        ] = signature

        return signature

    def _occupancy_dict_from_signature(
        self,
        signature
    ):
        return {
            station_id: count
            for station_id, count
            in signature
        }

    def _active_segment_for_manipulator_at(
        self,
        manipulator_id,
        time_value
    ):
        for segment in self._segments_by_manipulator().get(
            int(
                manipulator_id
            ),
            []
        ):
            if (
                float(
                    segment.start_time
                )
                <=
                float(
                    time_value
                )
                <
                float(
                    segment.end_time
                )
            ):
                return segment

        return None

    def _last_segment_before_time(
        self,
        manipulator_id,
        time_value
    ):
        candidate = None

        for segment in self._segments_by_manipulator().get(
            int(
                manipulator_id
            ),
            []
        ):
            if (
                float(
                    segment.end_time
                )
                <=
                float(
                    time_value
                )
            ):
                if (
                    candidate is None
                    or
                    float(
                        segment.end_time
                    )
                    >
                    float(
                        candidate.end_time
                    )
                ):
                    candidate = segment

        return candidate

    def _position_on_segment(
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
            return end_position

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

    def _manipulator_position_at(
        self,
        manipulator_id,
        time_value
    ):
        segment = (
            self._active_segment_for_manipulator_at(
                manipulator_id,
                time_value
            )
        )

        if segment is not None:
            return self._position_on_segment(
                segment,
                time_value
            )

        last_segment = (
            self._last_segment_before_time(
                manipulator_id,
                time_value
            )
        )

        if last_segment is not None:
            return float(
                last_segment.end_position
            )

        return float(
            self._configured_manipulator_positions().get(
                int(
                    manipulator_id
                ),
                0
            )
        )

    def _manipulator_carrying_at(
        self,
        manipulator_id,
        time_value
    ):
        segment = (
            self._active_segment_for_manipulator_at(
                manipulator_id,
                time_value
            )
        )

        if segment is None:
            return False

        return (
            getattr(
                segment,
                "hanger_id",
                None
            )
            is not None
        )

    def _manipulator_signature_at(
        self,
        time_value
    ):
        key = round(
            float(
                time_value
            ),
            3
        )

        if key in self._manipulator_signature_cache:
            return self._manipulator_signature_cache[
                key
            ]

        signature = []

        for manipulator_id in self._manipulator_ids():
            position = self._manipulator_position_at(
                manipulator_id,
                key
            )

            carrying = self._manipulator_carrying_at(
                manipulator_id,
                key
            )

            signature.append(
                (
                    int(
                        manipulator_id
                    ),
                    int(
                        round(
                            position
                        )
                    ),
                    1
                    if carrying
                    else
                    0
                )
            )

        signature = tuple(
            sorted(
                signature
            )
        )

        self._manipulator_signature_cache[
            key
        ] = signature

        return signature

    def _manipulator_signature_to_dict(
        self,
        signature
    ):
        return {
            manipulator_id: (
                position,
                loaded
            )
            for manipulator_id, position, loaded
            in signature
        }

    def _boundary_errors_at(
        self,
        time_value,
        label
    ):
        key = (
            round(
                float(
                    time_value
                ),
                3
            ),
            label
        )

        if key in self._boundary_errors_cache:
            return self._boundary_errors_cache[
                key
            ]

        errors = []

        for manipulator_id in self._manipulator_ids():
            segment = (
                self._active_segment_for_manipulator_at(
                    manipulator_id,
                    time_value
                )
            )

            if segment is None:
                continue

            segment_type = str(
                getattr(
                    segment,
                    "segment_type",
                    ""
                )
            )

            if segment_type == self.SEGMENT_IDLE:
                continue

            if (
                abs(
                    float(
                        segment.end_time
                    )
                    -
                    float(
                        segment.start_time
                    )
                )
                <=
                self.TIME_TOLERANCE
            ):
                continue

            errors.append(
                (
                    f"M{manipulator_id}: granica {label} wypada "
                    f"w trakcie ruchu {segment_type}, "
                    f"t={float(time_value):.1f}, "
                    f"segment={float(segment.start_time):.1f}"
                    f"..{float(segment.end_time):.1f}."
                )
            )

        self._boundary_errors_cache[
            key
        ] = errors

        return errors

    def _transport_signature(
        self,
        start_time,
        end_time
    ):
        key = (
            round(
                float(
                    start_time
                ),
                3
            ),
            round(
                float(
                    end_time
                ),
                3
            )
        )

        if key in self._transport_signature_cache:
            return self._transport_signature_cache[
                key
            ]

        signature = []

        for task in self._tasks_in_window(
            start_time,
            end_time
        ):
            signature.append(
                (
                    int(
                        task.manipulator_id
                    ),
                    int(
                        task.source_station
                    ),
                    int(
                        task.target_station
                    )
                )
            )

        signature = tuple(
            signature
        )

        self._transport_signature_cache[
            key
        ] = signature

        return signature

    def _trajectory_signature(
        self,
        start_time,
        end_time
    ):
        key = (
            round(
                float(
                    start_time
                ),
                3
            ),
            round(
                float(
                    end_time
                ),
                3
            )
        )

        if key in self._trajectory_signature_cache:
            return self._trajectory_signature_cache[
                key
            ]

        signature = []

        for segment in self._segments_in_window(
            start_time,
            end_time
        ):
            segment_type = str(
                getattr(
                    segment,
                    "segment_type",
                    ""
                )
            )

            if segment_type == self.SEGMENT_IDLE:
                continue

            signature.append(
                (
                    int(
                        segment.manipulator_id
                    ),
                    segment_type,
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

        signature = tuple(
            signature
        )

        self._trajectory_signature_cache[
            key
        ] = signature

        return signature

    def _neighbor_pattern_match(
        self,
        start_time,
        end_time
    ):
        duration = (
            float(
                end_time
            )
            -
            float(
                start_time
            )
        )

        if duration <= 0:
            return (
                False,
                "duration<=0"
            )

        final_time = float(
            getattr(
                self.result,
                "final_time",
                0.0
            )
        )

        current_transport = self._transport_signature(
            start_time,
            end_time
        )

        current_trajectory = self._trajectory_signature(
            start_time,
            end_time
        )

        if not current_transport:
            return (
                False,
                "empty transport signature"
            )

        if not current_trajectory:
            return (
                False,
                "empty trajectory signature"
            )

        next_start = (
            float(
                end_time
            )
        )

        next_end = (
            next_start
            +
            duration
        )

        if (
            next_end
            <=
            final_time
        ):
            next_transport = self._transport_signature(
                next_start,
                next_end
            )

            next_trajectory = self._trajectory_signature(
                next_start,
                next_end
            )

            if (
                current_transport
                ==
                next_transport
                and
                current_trajectory
                ==
                next_trajectory
            ):
                return (
                    True,
                    "matches next window"
                )

        previous_end = (
            float(
                start_time
            )
        )

        previous_start = (
            previous_end
            -
            duration
        )

        if previous_start >= 0.0:
            previous_transport = self._transport_signature(
                previous_start,
                previous_end
            )

            previous_trajectory = self._trajectory_signature(
                previous_start,
                previous_end
            )

            if (
                current_transport
                ==
                previous_transport
                and
                current_trajectory
                ==
                previous_trajectory
            ):
                return (
                    True,
                    "matches previous window"
                )

        return (
            False,
            "no repeated transport+trajectory pattern"
        )

    def _estimated_empty_parking_steps(
        self,
        manipulator_id,
        start_time,
        end_time
    ):
        count = 0

        for segment in self._segments_in_window(
            start_time,
            end_time
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

            segment_type = str(
                getattr(
                    segment,
                    "segment_type",
                    ""
                )
            )

            if (
                segment_type
                not in self.EMPTY_SEGMENT_TYPES
            ):
                continue

            if (
                getattr(
                    segment,
                    "hanger_id",
                    None
                )
                is not None
            ):
                continue

            if (
                int(
                    round(
                        segment.start_position
                    )
                )
                ==
                int(
                    round(
                        segment.end_position
                    )
                )
            ):
                continue

            count += 1

        return count

    def _station_action_events(
        self,
        tasks,
        load_station,
        unload_station
    ):
        events_by_station = {}

        for task in tasks:
            source_station = int(
                task.source_station
            )

            target_station = int(
                task.target_station
            )

            if (
                source_station
                !=
                load_station
            ):
                events_by_station.setdefault(
                    source_station,
                    []
                ).append(
                    {
                        "time": float(
                            task.start_time
                        ),
                        "kind": self.ACTION_PICKUP,
                        "manipulator_id": int(
                            task.manipulator_id
                        ),
                        "hanger_id": int(
                            task.hanger_id
                        )
                    }
                )

            if (
                target_station
                !=
                unload_station
            ):
                events_by_station.setdefault(
                    target_station,
                    []
                ).append(
                    {
                        "time": float(
                            task.end_time
                        ),
                        "kind": self.ACTION_DROP,
                        "manipulator_id": int(
                            task.manipulator_id
                        ),
                        "hanger_id": int(
                            task.hanger_id
                        )
                    }
                )

        for station_id in events_by_station:
            events_by_station[
                station_id
            ].sort(
                key=lambda event:
                    (
                        float(
                            event[
                                "time"
                            ]
                        ),
                        0
                        if event[
                            "kind"
                        ]
                        ==
                        self.ACTION_PICKUP
                        else
                        1,
                        int(
                            event[
                                "manipulator_id"
                            ]
                        ),
                        int(
                            event[
                                "hanger_id"
                            ]
                        )
                    )
            )

        return events_by_station

    def _phase_for_station_with_initial(
        self,
        station_id,
        initial_occupancy,
        events
    ):
        occupancy = int(
            initial_occupancy
        )

        min_occupancy = occupancy
        max_occupancy = occupancy
        previous_kind = None
        errors = []

        for event in events:
            kind = event[
                "kind"
            ]

            if kind == self.ACTION_PICKUP:
                if occupancy <= 0:
                    errors.append(
                        (
                            f"S{station_id}: PICKUP przy pustej stacji "
                            f"t={event['time']:.1f}, "
                            f"M{event['manipulator_id']}, "
                            f"H{event['hanger_id']}."
                        )
                    )

                occupancy -= 1

            elif kind == self.ACTION_DROP:
                if occupancy >= 1:
                    errors.append(
                        (
                            f"S{station_id}: DROP na zajętą stację "
                            f"t={event['time']:.1f}, "
                            f"M{event['manipulator_id']}, "
                            f"H{event['hanger_id']}."
                        )
                    )

                occupancy += 1

            if (
                previous_kind is not None
                and
                previous_kind
                ==
                kind
            ):
                errors.append(
                    (
                        f"S{station_id}: dwie kolejne akcje {kind} "
                        f"bez akcji przeciwnej t={event['time']:.1f}."
                    )
                )

            previous_kind = kind
            min_occupancy = min(
                min_occupancy,
                occupancy
            )
            max_occupancy = max(
                max_occupancy,
                occupancy
            )

        if occupancy != initial_occupancy:
            errors.append(
                (
                    f"S{station_id}: faza nie wraca do stanu startowego "
                    f"start={initial_occupancy}, end={occupancy}."
                )
            )

        if (
            min_occupancy
            <
            0
            or
            max_occupancy
            >
            1
        ):
            errors.append(
                (
                    f"S{station_id}: pojemność 1 naruszona, "
                    f"min={min_occupancy}, max={max_occupancy}."
                )
            )

        return (
            occupancy,
            errors
        )

    def _phase_analysis(
        self,
        tasks,
        start_time,
        end_time,
        load_station,
        unload_station
    ):
        start_signature = self._occupancy_signature_at(
            start_time
        )

        end_signature = self._occupancy_signature_at(
            end_time
        )

        start_dict = self._occupancy_dict_from_signature(
            start_signature
        )

        end_dict = self._occupancy_dict_from_signature(
            end_signature
        )

        events_by_station = self._station_action_events(
            tasks,
            load_station,
            unload_station
        )

        station_ids = set(
            start_dict.keys()
        )

        station_ids.update(
            end_dict.keys()
        )

        station_ids.update(
            events_by_station.keys()
        )

        station_initial_phase = {}
        station_final_phase = {}
        errors = []

        for station_id in sorted(
            station_ids
        ):
            initial = int(
                start_dict.get(
                    station_id,
                    0
                )
            )

            expected_end = int(
                end_dict.get(
                    station_id,
                    0
                )
            )

            simulated_end, station_errors = (
                self._phase_for_station_with_initial(
                    station_id,
                    initial,
                    events_by_station.get(
                        station_id,
                        []
                    )
                )
            )

            station_initial_phase[
                station_id
            ] = initial

            station_final_phase[
                station_id
            ] = expected_end

            if simulated_end != expected_end:
                station_errors.append(
                    (
                        f"S{station_id}: symulowana faza końcowa "
                        f"{simulated_end} różni się od rzeczywistej "
                        f"{expected_end}."
                    )
                )

            if initial != expected_end:
                station_errors.append(
                    (
                        f"S{station_id}: zajętość na granicy cyklu "
                        f"nie jest identyczna start={initial}, "
                        f"end={expected_end}."
                    )
                )

            errors.extend(
                station_errors
            )

        return (
            station_initial_phase,
            station_final_phase,
            errors
        )

    def _manipulator_phase_analysis(
        self,
        start_time,
        end_time
    ):
        start_signature = self._manipulator_signature_at(
            start_time
        )

        end_signature = self._manipulator_signature_at(
            end_time
        )

        start_dict = self._manipulator_signature_to_dict(
            start_signature
        )

        end_dict = self._manipulator_signature_to_dict(
            end_signature
        )

        configured_positions = self._configured_manipulator_positions()

        errors = []
        position_penalty = 0.0

        for manipulator_id in self._manipulator_ids():
            start_position, start_loaded = start_dict.get(
                manipulator_id,
                (
                    None,
                    None
                )
            )

            end_position, end_loaded = end_dict.get(
                manipulator_id,
                (
                    None,
                    None
                )
            )

            if (
                start_position
                !=
                end_position
                or
                start_loaded
                !=
                end_loaded
            ):
                errors.append(
                    (
                        f"M{manipulator_id}: faza manipulatora nie jest "
                        f"zamknięta, start=({start_position}, "
                        f"loaded={start_loaded}), end=({end_position}, "
                        f"loaded={end_loaded})."
                    )
                )

            configured_position = configured_positions.get(
                manipulator_id
            )

            if (
                configured_position is not None
                and
                start_position is not None
            ):
                position_penalty += abs(
                    float(
                        start_position
                    )
                    -
                    float(
                        configured_position
                    )
                )

            if start_loaded:
                errors.append(
                    (
                        f"M{manipulator_id}: manipulator ma zawieszkę "
                        f"na początku cyklu."
                    )
                )

            if end_loaded:
                errors.append(
                    (
                        f"M{manipulator_id}: manipulator ma zawieszkę "
                        f"na końcu cyklu."
                    )
                )

        errors.extend(
            self._boundary_errors_at(
                start_time,
                "START"
            )
        )

        errors.extend(
            self._boundary_errors_at(
                end_time,
                "END"
            )
        )

        return (
            start_dict,
            end_dict,
            errors,
            position_penalty
        )

    def _quick_reject(
        self,
        start_time,
        end_time
    ):
        if (
            self._occupancy_signature_at(
                start_time
            )
            !=
            self._occupancy_signature_at(
                end_time
            )
        ):
            return True

        if (
            self._manipulator_signature_at(
                start_time
            )
            !=
            self._manipulator_signature_at(
                end_time
            )
        ):
            return True

        if self._boundary_errors_at(
            start_time,
            "START"
        ):
            return True

        if self._boundary_errors_at(
            end_time,
            "END"
        ):
            return True

        return False

    def _throughput_physics_penalty(
        self,
        tasks,
        duration
    ):
        if (
            duration
            <=
            0.0
        ):
            return (
                999999.0,
                []
            )

        capacities = self._station_capacity_groups()

        group_counts = {}
        group_limits = {}

        _load_station, unload_station = (
            self._load_unload_stations()
        )

        for task in tasks:
            station_id = int(
                task.target_station
            )

            if station_id == unload_station:
                continue

            info = capacities.get(
                station_id
            )

            if info is None:
                continue

            key = info[
                "key"
            ]

            group_counts[
                key
            ] = (
                group_counts.get(
                    key,
                    0
                )
                +
                1
            )

            group_limits[
                key
            ] = info

        errors = []
        penalty = 0.0

        for key, count in group_counts.items():
            info = group_limits[
                key
            ]

            min_time = float(
                info[
                    "min_time"
                ]
            )

            capacity = int(
                info[
                    "capacity"
                ]
            )

            if min_time <= 0.0:
                continue

            minimum_required_time = (
                count
                *
                min_time
                /
                max(
                    1,
                    capacity
                )
            )

            if (
                minimum_required_time
                >
                duration
                +
                self.TIME_TOLERANCE
            ):
                exceed = (
                    minimum_required_time
                    -
                    duration
                )

                penalty += (
                    exceed
                    *
                    10000.0
                )

                errors.append(
                    (
                        f"Fizyczny limit procesu naruszony dla {key}: "
                        f"count={count}, min={min_time:.1f}s, "
                        f"capacity={capacity}, "
                        f"wymagane>={minimum_required_time:.1f}s, "
                        f"okno={duration:.1f}s."
                    )
                )

        return (
            penalty,
            errors
        )

    @property
    def candidate_cache_stats(self):
        """Return deterministic counters useful during CPU profiling."""
        return {
            "hits": self._candidate_cache_hits,
            "misses": self._candidate_cache_misses,
            "size": len(self._candidate_cache)
        }

    @staticmethod
    def _candidate_cache_key(start, end, seed_start, seed_duration):
        return tuple(round(float(value), 6) for value in (
            start, end, seed_start, seed_duration
        ))

    @staticmethod
    def _copy_cached_candidate(candidate):
        cloned = copy(candidate)
        cloned.messages = list(getattr(candidate, "messages", []))
        return cloned

    def _candidate(
        self,
        start,
        end,
        seed_start,
        seed_duration
    ):
        key = self._candidate_cache_key(
            start, end, seed_start, seed_duration
        )
        cached = self._candidate_cache.get(key)
        if cached is not None:
            self._candidate_cache_hits += 1
            return self._copy_cached_candidate(cached)
        self._candidate_cache_misses += 1
        candidate = self._candidate_uncached(
            start, end, seed_start, seed_duration
        )
        self._candidate_cache[key] = candidate
        return self._copy_cached_candidate(candidate)

    def _candidate_uncached(
        self,
        start_time,
        end_time,
        seed_start,
        seed_duration
    ):
        load_station, unload_station = self._load_unload_stations()

        tasks = self._tasks_in_window(
            start_time,
            end_time
        )

        duration = (
            float(
                end_time
            )
            -
            float(
                start_time
            )
        )

        transport_counts = {}

        balance = {}

        for task in tasks:
            manipulator_id = int(
                task.manipulator_id
            )

            transport_counts[
                manipulator_id
            ] = (
                transport_counts.get(
                    manipulator_id,
                    0
                )
                +
                1
            )

            source_station = int(
                task.source_station
            )

            target_station = int(
                task.target_station
            )

            if source_station != load_station:
                balance[
                    source_station
                ] = (
                    balance.get(
                        source_station,
                        0
                    )
                    -
                    1
                )

                if balance[
                    source_station
                ] == 0:
                    del balance[
                        source_station
                    ]

            if target_station != unload_station:
                balance[
                    target_station
                ] = (
                    balance.get(
                        target_station,
                        0
                    )
                    +
                    1
                )

                if balance[
                    target_station
                ] == 0:
                    del balance[
                        target_station
                    ]

        logical_steps = {}

        for manipulator_id, transport_count in transport_counts.items():
            empty_steps = self._estimated_empty_parking_steps(
                manipulator_id,
                start_time,
                end_time
            )

            logical_steps[
                manipulator_id
            ] = (
                transport_count
                *
                2
                +
                empty_steps
            )

        station_initial_phase, station_final_phase, station_errors = (
            self._phase_analysis(
                tasks,
                start_time,
                end_time,
                load_station,
                unload_station
            )
        )

        (
            manipulator_initial_phase,
            manipulator_final_phase,
            manipulator_errors,
            manipulator_position_penalty
        ) = self._manipulator_phase_analysis(
            start_time,
            end_time
        )

        pattern_ok, pattern_reason = self._neighbor_pattern_match(
            start_time,
            end_time
        )

        physics_penalty, physics_errors = (
            self._throughput_physics_penalty(
                tasks,
                duration
            )
        )

        balance_error = sum(
            abs(
                value
            )
            for value
            in balance.values()
        )

        over_limit = 0

        messages = []

        for manipulator_id, step_count in logical_steps.items():
            if step_count > self.max_logical_steps:
                over_limit += (
                    step_count
                    -
                    self.max_logical_steps
                )

                messages.append(
                    (
                        f"M{manipulator_id}: {step_count} kroków "
                        f"logicznych, limit={self.max_logical_steps}. "
                        f"Liczenie uwzględnia parkingi."
                    )
                )

        if not tasks:
            messages.append(
                "Brak transportów w oknie."
            )

        if balance_error > 0:
            messages.append(
                f"Bilans materiałowy niezamyka się: {balance}"
            )

        if station_errors:
            messages.append(
                f"Błędy fazy stanowisk: {len(station_errors)}"
            )

        if manipulator_errors:
            messages.append(
                f"Błędy fazy manipulatorów: {len(manipulator_errors)}"
            )

        if not pattern_ok:
            messages.append(
                f"Brak powtarzalnego wzorca: {pattern_reason}"
            )
        else:
            messages.append(
                f"Wzorzec cyklu OK: {pattern_reason}"
            )

        for message in (
            station_errors
            +
            manipulator_errors
            +
            physics_errors
        )[
            :20
        ]:
            messages.append(
                message
            )

        messages.append(
            (
                "Faza manipulatorów START: "
                f"{dict(sorted(manipulator_initial_phase.items()))}"
            )
        )

        messages.append(
            (
                "Faza manipulatorów END: "
                f"{dict(sorted(manipulator_final_phase.items()))}"
            )
        )

        messages.append(
            (
                "Transport signature length: "
                f"{len(self._transport_signature(start_time, end_time))}"
            )
        )

        messages.append(
            (
                "Trajectory signature length: "
                f"{len(self._trajectory_signature(start_time, end_time))}"
            )
        )

        valid = (
            len(
                tasks
            )
            >
            0
            and
            balance_error
            ==
            0
            and
            over_limit
            ==
            0
            and
            len(
                station_errors
            )
            ==
            0
            and
            len(
                manipulator_errors
            )
            ==
            0
            and
            len(
                physics_errors
            )
            ==
            0
            and
            pattern_ok
        )

        duration_distance = abs(
            duration
            -
            seed_duration
        )

        start_distance = abs(
            float(
                start_time
            )
            -
            float(
                seed_start
            )
        )

        score = (
            balance_error
            *
            1000000.0
            +
            len(
                station_errors
            )
            *
            500000.0
            +
            len(
                manipulator_errors
            )
            *
            400000.0
            +
            (
                0.0
                if pattern_ok
                else 300000.0
            )
            +
            physics_penalty
            +
            over_limit
            *
            50000.0
            +
            manipulator_position_penalty
            *
            1000.0
            +
            duration_distance
            *
            1.0
            +
            start_distance
            *
            0.05
            -
            len(
                tasks
            )
            *
            0.1
        )

        return MaterialCycleCandidate(
            start_time=(
                float(
                    start_time
                )
            ),
            end_time=(
                float(
                    end_time
                )
            ),
            duration=(
                float(
                    duration
                )
            ),
            total_transports=(
                len(
                    tasks
                )
            ),
            balance=(
                dict(
                    sorted(
                        balance.items()
                    )
                )
            ),
            transport_counts_by_manipulator=(
                dict(
                    sorted(
                        transport_counts.items()
                    )
                )
            ),
            logical_steps_by_manipulator=(
                dict(
                    sorted(
                        logical_steps.items()
                    )
                )
            ),
            station_initial_phase=(
                dict(
                    sorted(
                        station_initial_phase.items()
                    )
                )
            ),
            station_final_phase=(
                dict(
                    sorted(
                        station_final_phase.items()
                    )
                )
            ),
            manipulator_initial_phase=(
                {
                    int(
                        manipulator_id
                    ): (
                        int(
                            position
                        ),
                        int(
                            loaded
                        )
                    )
                    for manipulator_id, (
                        position,
                        loaded
                    )
                    in dict(
                        sorted(
                            manipulator_initial_phase.items()
                        )
                    ).items()
                }
            ),
            manipulator_final_phase=(
                {
                    int(
                        manipulator_id
                    ): (
                        int(
                            position
                        ),
                        int(
                            loaded
                        )
                    )
                    for manipulator_id, (
                        position,
                        loaded
                    )
                    in dict(
                        sorted(
                            manipulator_final_phase.items()
                        )
                    ).items()
                }
            ),
            phase_errors=(
                station_errors
                +
                manipulator_errors
                +
                physics_errors
                +
                (
                    []
                    if pattern_ok
                    else [
                        pattern_reason
                    ]
                )
            ),
            score=(
                score
            ),
            valid=(
                valid
            ),
            messages=(
                messages
            )
        )

    def _candidate_times(
        self,
        analysis_start,
        analysis_end,
        time_step
    ):
        times = set()

        current = (
            round(
                analysis_start
                /
                time_step
            )
            *
            time_step
        )

        while current <= analysis_end:
            times.add(
                round(
                    current,
                    3
                )
            )

            current += time_step

        for task in self._all_tasks():
            for value in [
                task.start_time,
                task.end_time
            ]:
                value = float(
                    value
                )

                if (
                    analysis_start
                    <=
                    value
                    <=
                    analysis_end
                ):
                    times.add(
                        round(
                            value,
                            3
                        )
                    )

        for segment in self._all_segments():
            for value in [
                segment.start_time,
                segment.end_time
            ]:
                value = float(
                    value
                )

                if (
                    analysis_start
                    <=
                    value
                    <=
                    analysis_end
                ):
                    times.add(
                        round(
                            value,
                            3
                        )
                    )

        return sorted(
            times
        )

    def _trim_times_near_seed(
        self,
        times,
        seed,
        max_count
    ):
        if (
            max_count is None
            or
            len(
                times
            )
            <=
            max_count
        ):
            return times

        ranked = sorted(
            times,
            key=lambda value:
                abs(
                    float(
                        value
                    )
                    -
                    float(
                        seed
                    )
                )
        )

        return sorted(
            ranked[
                :max_count
            ]
        )

    def find_best(
        self,
        seed_start,
        seed_end,
        search_radius=1800.0,
        min_duration=120.0,
        max_duration=4200.0,
        time_step=20.0,
        duration_step=10.0
    ):
        seed_start = float(
            seed_start
        )

        seed_end = float(
            seed_end
        )

        seed_duration = max(
            1.0,
            seed_end
            -
            seed_start
        )

        final_time = float(
            getattr(
                self.result,
                "final_time",
                0.0
            )
        )

        analysis_start = max(
            0.0,
            seed_start
            -
            float(
                search_radius
            )
        )

        analysis_end = min(
            final_time,
            seed_start
            +
            float(
                search_radius
            )
        )

        duration_min = max(
            float(
                min_duration
            ),
            seed_duration
            -
            float(
                search_radius
            )
        )

        duration_max = min(
            float(
                max_duration
            ),
            seed_duration
            +
            float(
                search_radius
            )
        )

        start_times = self._candidate_times(
            analysis_start,
            analysis_end,
            time_step
        )

        end_times = self._candidate_times(
            analysis_start,
            min(
                final_time,
                analysis_end
                +
                duration_max
            ),
            time_step
        )

        start_times = self._trim_times_near_seed(
            start_times,
            seed_start,
            500
        )

        end_times = sorted(
            end_times
        )

        best_valid = None
        best_any = None

        evaluated_quick = 0
        evaluated_full = 0

        max_full_candidates = 30000

        for start in start_times:
            lower = (
                start
                +
                duration_min
            )

            upper = (
                start
                +
                duration_max
            )

            left_index = bisect_left(
                end_times,
                lower
            )

            right_index = bisect_right(
                end_times,
                upper
            )

            possible_ends = end_times[
                left_index:
                right_index
            ]

            possible_ends = sorted(
                possible_ends,
                key=lambda end:
                    (
                        abs(
                            (
                                end
                                -
                                start
                            )
                            -
                            seed_duration
                        ),
                        abs(
                            start
                            -
                            seed_start
                        )
                    )
            )

            for end in possible_ends:
                if (
                    end
                    <=
                    start
                    or
                    end
                    >
                    final_time
                ):
                    continue

                evaluated_quick += 1

                if self._quick_reject(
                    start,
                    end
                ):
                    continue

                pattern_ok, _reason = self._neighbor_pattern_match(
                    start,
                    end
                )

                if not pattern_ok:
                    continue

                evaluated_full += 1

                candidate = self._candidate(
                    start,
                    end,
                    seed_start,
                    seed_duration
                )

                if (
                    best_any is None
                    or
                    candidate.score
                    <
                    best_any.score
                ):
                    best_any = candidate

                if candidate.valid:
                    if (
                        best_valid is None
                        or
                        candidate.score
                        <
                        best_valid.score
                    ):
                        best_valid = candidate

                if evaluated_full >= max_full_candidates:
                    break

            if evaluated_full >= max_full_candidates:
                break

        if best_valid is not None:
            best_valid.messages.append(
                (
                    f"Cycle search strategy: repeated "
                    f"transport+trajectory signature."
                )
            )

            best_valid.messages.append(
                (
                    f"Cycle search candidates: quick={evaluated_quick}, "
                    f"full={evaluated_full}."
                )
            )

            return best_valid

        if best_any is not None:
            best_any.messages.append(
                (
                    f"Cycle search strategy: repeated "
                    f"transport+trajectory signature."
                )
            )

            best_any.messages.append(
                (
                    f"Cycle search candidates: quick={evaluated_quick}, "
                    f"full={evaluated_full}."
                )
            )

            return best_any

        fallback_pairs = []

        for start in self._trim_times_near_seed(
            start_times,
            seed_start,
            120
        ):
            lower = (
                start
                +
                duration_min
            )

            upper = (
                start
                +
                duration_max
            )

            left_index = bisect_left(
                end_times,
                lower
            )

            right_index = bisect_right(
                end_times,
                upper
            )

            for end in end_times[
                left_index:
                right_index
            ]:
                if (
                    end
                    <=
                    start
                    or
                    end
                    >
                    final_time
                ):
                    continue

                fallback_pairs.append(
                    (
                        abs(
                            (
                                end
                                -
                                start
                            )
                            -
                            seed_duration
                        )
                        +
                        abs(
                            start
                            -
                            seed_start
                        )
                        *
                        0.05,
                        start,
                        end
                    )
                )

        fallback_pairs.sort(
            key=lambda item:
                item[
                    0
                ]
        )

        for _score, start, end in fallback_pairs[
            :3000
        ]:
            if self._quick_reject(
                start,
                end
            ):
                continue

            candidate = self._candidate(
                start,
                end,
                seed_start,
                seed_duration
            )

            if (
                best_any is None
                or
                candidate.score
                <
                best_any.score
            ):
                best_any = candidate

            if candidate.valid:
                if (
                    best_valid is None
                    or
                    candidate.score
                    <
                    best_valid.score
                ):
                    best_valid = candidate

        if best_valid is not None:
            best_valid.messages.append(
                "Cycle search used fallback pass."
            )

            return best_valid

        if best_any is not None:
            best_any.messages.append(
                "Cycle search returned best invalid fallback candidate."
            )

        return best_any