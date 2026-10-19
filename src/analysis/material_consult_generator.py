from src.model.program_consult import (
    ProgramConsult
)


class MaterialConsultGenerator:

    ACTION_PICKUP = 1
    ACTION_DROP = 2

    REASON_MATERIAL_AVAILABLE = "MATERIAL_AVAILABLE"
    REASON_STATION_CLEAR = "STATION_CLEAR"

    def __init__(
        self,
        programs,
        initial_station_occupancy=None,
        load_station=None,
        unload_station=None
    ):
        self.programs = (
            programs
            or
            {}
        )

        self.initial_station_occupancy = (
            self._normalize_occupancy(
                initial_station_occupancy
            )
        )

        self.load_station = (
            load_station
        )

        self.unload_station = (
            unload_station
        )

    def generate(
        self
    ):
        consults = []

        interactions_by_station = (
            self._interactions_by_station()
        )

        for station_id, interactions in sorted(
            interactions_by_station.items()
        ):
            if (
                station_id
                ==
                self.load_station
                or
                station_id
                ==
                self.unload_station
            ):
                continue

            if (
                len(
                    interactions
                )
                <
                2
            ):
                continue

            interactions.sort(
                key=lambda item:
                    (
                        item[
                            "cycle_time_start"
                        ],
                        item[
                            "manipulator_id"
                        ],
                        item[
                            "step"
                        ].step_no
                    )
            )

            consults.extend(
                self._consults_for_station_interactions(
                    station_id=(
                        station_id
                    ),
                    interactions=(
                        interactions
                    )
                )
            )

        return self._deduplicate(
            consults
        )

    def _normalize_occupancy(
        self,
        initial_station_occupancy
    ):
        if not initial_station_occupancy:
            return {}

        result = {}

        for station_id, occupancy in initial_station_occupancy.items():
            try:
                station_id = int(
                    station_id
                )
                occupancy = int(
                    occupancy
                )
            except Exception:
                continue

            if occupancy <= 0:
                continue

            result[
                station_id
            ] = (
                occupancy
            )

        return result

    def _consults_for_station_interactions(
        self,
        station_id,
        interactions
    ):
        consults = []

        #
        # Bardzo ważne:
        # NIE ROBIMY zawijania ostatni->pierwszy.
        #
        # Stan początkowy cyklu jest już odtworzony przez
        # initial_station_occupancy, więc pierwszy PICKUP ze stacji
        # początkowo zajętej nie powinien czekać na ostatni DROP cyklu.
        #
        previous = None

        occupancy = int(
            self.initial_station_occupancy.get(
                station_id,
                0
            )
        )

        for current in interactions:

            current_action = (
                current[
                    "action"
                ]
            )

            if previous is not None:

                previous_action = (
                    previous[
                        "action"
                    ]
                )

                #
                # PICKUP po DROP:
                # bieżący PICKUP może nastąpić dopiero po zakończeniu
                # poprzedniego DROP na tej samej stacji.
                #
                if (
                    current_action
                    ==
                    self.ACTION_PICKUP
                    and
                    previous_action
                    ==
                    self.ACTION_DROP
                    and
                    current[
                        "manipulator_id"
                    ]
                    !=
                    previous[
                        "manipulator_id"
                    ]
                ):
                    consults.append(
                        self._build_consult(
                            source=(
                                current
                            ),
                            target=(
                                previous
                            ),
                            source_plc_index=(
                                self._station_word_index(
                                    current[
                                        "step"
                                    ].step_no
                                )
                            ),
                            target_plc_index=(
                                self._action_word_index(
                                    previous[
                                        "step"
                                    ].step_no
                                )
                            ),
                            reason=(
                                self.REASON_MATERIAL_AVAILABLE
                            ),
                            description=(
                                f"Material S{station_id}: "
                                f"M{current['manipulator_id']} PICKUP "
                                f"czeka na M{previous['manipulator_id']} DROP."
                            )
                        )
                    )

                #
                # DROP po PICKUP:
                # bieżący DROP może nastąpić dopiero po zakończeniu
                # poprzedniego PICKUP, bo dopiero wtedy stacja jest wolna.
                #
                elif (
                    current_action
                    ==
                    self.ACTION_DROP
                    and
                    previous_action
                    ==
                    self.ACTION_PICKUP
                    and
                    current[
                        "manipulator_id"
                    ]
                    !=
                    previous[
                        "manipulator_id"
                    ]
                ):
                    consults.append(
                        self._build_consult(
                            source=(
                                current
                            ),
                            target=(
                                previous
                            ),
                            source_plc_index=(
                                self._station_word_index(
                                    current[
                                        "step"
                                    ].step_no
                                )
                            ),
                            target_plc_index=(
                                self._action_word_index(
                                    previous[
                                        "step"
                                    ].step_no
                                )
                            ),
                            reason=(
                                self.REASON_STATION_CLEAR
                            ),
                            description=(
                                f"Clear S{station_id}: "
                                f"M{current['manipulator_id']} DROP "
                                f"czeka na M{previous['manipulator_id']} PICKUP."
                            )
                        )
                    )

            #
            # Lokalna symulacja fazy tylko diagnostycznie.
            # Nie generujemy consultu "z przyszłości" dla pierwszej akcji.
            #
            if (
                current_action
                ==
                self.ACTION_PICKUP
            ):
                occupancy -= 1

            elif (
                current_action
                ==
                self.ACTION_DROP
            ):
                occupancy += 1

            previous = (
                current
            )

        return consults

    def _interactions_by_station(
        self
    ):
        result = {}

        for manipulator_id in sorted(
            self.programs.keys()
        ):
            program = (
                self.programs[
                    manipulator_id
                ]
            )

            for step in getattr(
                program,
                "steps",
                []
            ):
                if (
                    getattr(
                        step,
                        "segment_type",
                        ""
                    )
                    ==
                    "empty_parking"
                ):
                    continue

                try:
                    action = int(
                        step.action
                    )
                except Exception:
                    continue

                if action not in [
                    self.ACTION_PICKUP,
                    self.ACTION_DROP
                ]:
                    continue

                station_id = int(
                    round(
                        step.station_id
                    )
                )

                if station_id not in result:
                    result[
                        station_id
                    ] = []

                result[
                    station_id
                ].append(
                    {
                        "program": program,
                        "manipulator_id": int(
                            manipulator_id
                        ),
                        "step": step,
                        "station_id": station_id,
                        "action": action,
                        "cycle_time_start": float(
                            getattr(
                                step,
                                "cycle_time_start",
                                0.0
                            )
                        )
                    }
                )

        return result

    def _build_consult(
        self,
        source,
        target,
        source_plc_index,
        target_plc_index,
        reason,
        description
    ):
        source_program = (
            source[
                "program"
            ]
        )

        target_program = (
            target[
                "program"
            ]
        )

        source_step = (
            source[
                "step"
            ]
        )

        target_step = (
            target[
                "step"
            ]
        )

        return ProgramConsult(
            source_manipulator_id=(
                int(
                    source_program.manipulator_id
                )
            ),
            source_logical_step_no=(
                int(
                    source_step.step_no
                )
            ),
            source_plc_index=(
                int(
                    source_plc_index
                )
            ),
            source_word_address=(
                int(
                    source_program.index_address
                )
                +
                int(
                    source_plc_index
                )
            ),
            target_manipulator_id=(
                int(
                    target_program.manipulator_id
                )
            ),
            target_logical_step_no=(
                int(
                    target_step.step_no
                )
            ),
            target_plc_index=(
                int(
                    target_plc_index
                )
            ),
            target_word_address=(
                int(
                    target_program.index_address
                )
                +
                int(
                    target_plc_index
                )
            ),
            source_cycle_time_start=(
                float(
                    getattr(
                        source_step,
                        "cycle_time_start",
                        0.0
                    )
                )
            ),
            source_cycle_time_end=(
                self._effective_step_end(
                    source_step
                )
            ),
            target_cycle_time_start=(
                float(
                    getattr(
                        target_step,
                        "cycle_time_start",
                        0.0
                    )
                )
            ),
            target_cycle_time_end=(
                self._effective_step_end(
                    target_step
                )
            ),
            reason=(
                reason
            ),
            description=(
                description
            )
        )

    def _effective_step_end(
        self,
        step
    ):
        return (
            float(
                getattr(
                    step,
                    "cycle_time_end",
                    getattr(
                        step,
                        "cycle_time_start",
                        0.0
                    )
                )
            )
            +
            float(
                getattr(
                    step,
                    "wait_time_01s",
                    0
                )
            )
            /
            10.0
        )

    def _station_word_index(
        self,
        logical_step_no
    ):
        return (
            (
                int(
                    logical_step_no
                )
                -
                1
            )
            *
            3
            +
            1
        )

    def _action_word_index(
        self,
        logical_step_no
    ):
        return (
            (
                int(
                    logical_step_no
                )
                -
                1
            )
            *
            3
            +
            2
        )

    def _deduplicate(
        self,
        consults
    ):
        result = []
        seen = set()

        for consult in consults:
            key = (
                int(
                    consult.source_manipulator_id
                ),
                int(
                    consult.source_plc_index
                ),
                int(
                    consult.target_manipulator_id
                ),
                int(
                    consult.target_plc_index
                ),
                str(
                    getattr(
                        consult,
                        "reason",
                        ""
                    )
                )
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            result.append(
                consult
            )

        return result