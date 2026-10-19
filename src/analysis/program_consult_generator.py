from src.model.program_consult import (
    ProgramConsult
)


class ProgramConsultGenerator:

    def __init__(
        self,
        programs
    ):
        self.programs = programs
        self.skipped_consults = []

    def generate(
        self
    ):
        raw_consults = []

        for source_manipulator_id in sorted(
            self.programs.keys()
        ):
            source_program = (
                self.programs[
                    source_manipulator_id
                ]
            )

            for source_step in source_program.steps:

                if not getattr(
                    source_step,
                    "crosses_foreign_zone",
                    False
                ):
                    continue

                target_manipulator_id = getattr(
                    source_step,
                    "foreign_zone_owner",
                    None
                )

                if target_manipulator_id is None:
                    continue

                target_program = (
                    self.programs.get(
                        target_manipulator_id
                    )
                )

                if target_program is None:
                    continue

                target_step = (
                    self._find_best_target_step(
                        source_step=(
                            source_step
                        ),
                        target_steps=(
                            target_program.steps
                        )
                    )
                )

                if target_step is None:
                    continue

                source_plc_index = (
                    self._station_word_index(
                        source_step.step_no
                    )
                )

                target_plc_index = (
                    self._wait_word_index(
                        target_step.step_no
                    )
                )

                consult = ProgramConsult(
                    source_manipulator_id=(
                        source_manipulator_id
                    ),
                    source_logical_step_no=(
                        source_step.step_no
                    ),
                    source_plc_index=(
                        source_plc_index
                    ),
                    source_word_address=(
                        source_program.index_address
                        +
                        source_plc_index
                    ),
                    target_manipulator_id=(
                        target_manipulator_id
                    ),
                    target_logical_step_no=(
                        target_step.step_no
                    ),
                    target_plc_index=(
                        target_plc_index
                    ),
                    target_word_address=(
                        target_program.index_address
                        +
                        target_plc_index
                    ),
                    source_cycle_time_start=(
                        source_step.cycle_time_start
                    ),
                    source_cycle_time_end=(
                        self._effective_step_end(
                            source_step
                        )
                    ),
                    target_cycle_time_start=(
                        target_step.cycle_time_start
                    ),
                    target_cycle_time_end=(
                        self._effective_step_end(
                            target_step
                        )
                    ),
                    reason="FOREIGN_ZONE",
                    description=(
                        f"M{source_manipulator_id} "
                        f"index {source_plc_index} "
                        f"(krok logiczny {source_step.step_no}) "
                        f"wchodzi w strefę M{target_manipulator_id}. "
                        f"Czekaj aż M{target_manipulator_id} "
                        f"skończy index {target_plc_index} "
                        f"(krok logiczny {target_step.step_no})."
                    )
                )

                raw_consults.append(
                    consult
                )

        raw_consults.sort(
            key=lambda item:
                (
                    item.source_cycle_time_start,
                    item.source_manipulator_id,
                    item.source_plc_index,
                    item.target_manipulator_id,
                    item.target_plc_index
                )
        )

        reduced = (
            self._reduce_redundant_consults(
                raw_consults
            )
        )

        safe = (
            self._remove_cycle_creating_consults(
                reduced
            )
        )

        return safe

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

    def _wait_word_index(
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
            3
        )

    def _max_plc_index_for_program(
        self,
        program
    ):
        return (
            len(
                program.steps
            )
            *
            3
        )

    def _effective_step_end(
        self,
        step
    ):
        return (
            float(
                step.cycle_time_end
            )
            +
            (
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
        )

    def _find_best_target_step(
        self,
        source_step,
        target_steps
    ):
        if not target_steps:
            return None

        overlapping = []

        source_start = float(
            source_step.cycle_time_start
        )

        source_end = (
            self._effective_step_end(
                source_step
            )
        )

        for target_step in target_steps:

            target_start = float(
                target_step.cycle_time_start
            )

            target_end = (
                self._effective_step_end(
                    target_step
                )
            )

            overlap_start = max(
                source_start,
                target_start
            )

            overlap_end = min(
                source_end,
                target_end
            )

            overlap = (
                overlap_end
                -
                overlap_start
            )

            if overlap >= 0:
                overlapping.append(
                    (
                        overlap,
                        target_step
                    )
                )

        if overlapping:
            overlapping.sort(
                key=lambda item:
                    (
                        -item[
                            0
                        ],
                        self._effective_step_end(
                            item[
                                1
                            ]
                        )
                    )
            )

            return (
                overlapping[
                    0
                ][
                    1
                ]
            )

        candidates = []

        for target_step in target_steps:
            distance = abs(
                self._effective_step_end(
                    target_step
                )
                -
                source_start
            )

            candidates.append(
                (
                    distance,
                    target_step
                )
            )

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

    def _reduce_redundant_consults(
        self,
        consults
    ):
        if not consults:
            return []

        reduced = []
        previous = None

        for consult in consults:

            if previous is None:
                reduced.append(
                    consult
                )

                previous = (
                    consult
                )

                continue

            same_pair = (
                consult.source_manipulator_id
                ==
                previous.source_manipulator_id
                and
                consult.target_manipulator_id
                ==
                previous.target_manipulator_id
            )

            same_target_wait = (
                consult.target_plc_index
                ==
                previous.target_plc_index
            )

            close_source_index = (
                consult.source_plc_index
                <=
                previous.source_plc_index
                +
                3
            )

            if (
                same_pair
                and
                same_target_wait
                and
                close_source_index
            ):
                continue

            reduced.append(
                consult
            )

            previous = (
                consult
            )

        return reduced

    def _build_base_dependency_graph(
        self
    ):
        graph = {}

        for manipulator_id, program in self.programs.items():

            max_index = (
                self._max_plc_index_for_program(
                    program
                )
            )

            for plc_index in range(
                1,
                max_index
                +
                1
            ):
                node = (
                    manipulator_id,
                    plc_index
                )

                if node not in graph:
                    graph[
                        node
                    ] = set()

                if (
                    plc_index
                    <
                    max_index
                ):
                    next_node = (
                        manipulator_id,
                        plc_index
                        +
                        1
                    )

                    graph[
                        node
                    ].add(
                        next_node
                    )

                    if next_node not in graph:
                        graph[
                            next_node
                        ] = set()

        return graph

    def _consult_edge(
        self,
        consult
    ):
        prerequisite_node = (
            consult.target_manipulator_id,
            consult.target_plc_index
        )

        blocked_node = (
            consult.source_manipulator_id,
            consult.source_plc_index
        )

        return (
            prerequisite_node,
            blocked_node
        )

    def _remove_cycle_creating_consults(
        self,
        consults
    ):
        graph = (
            self._build_base_dependency_graph()
        )

        safe = []
        self.skipped_consults = []

        for consult in consults:

            source_node, target_node = (
                self._consult_edge(
                    consult
                )
            )

            if source_node not in graph:
                graph[
                    source_node
                ] = set()

            if target_node not in graph:
                graph[
                    target_node
                ] = set()

            if (
                self._path_exists(
                    graph,
                    start=(
                        target_node
                    ),
                    target=(
                        source_node
                    )
                )
            ):
                self.skipped_consults.append(
                    consult
                )

                print(
                    f"SKIP CONSULT CYCLE "
                    f"{consult.to_text()}"
                )

                continue

            graph[
                source_node
            ].add(
                target_node
            )

            safe.append(
                consult
            )

        return safe

    def _path_exists(
        self,
        graph,
        start,
        target
    ):
        if start == target:
            return True

        visited = set()
        stack = [
            start
        ]

        while stack:
            node = (
                stack.pop()
            )

            if node in visited:
                continue

            visited.add(
                node
            )

            for next_node in graph.get(
                node,
                set()
            ):
                if next_node == target:
                    return True

                if next_node not in visited:
                    stack.append(
                        next_node
                    )

        return False