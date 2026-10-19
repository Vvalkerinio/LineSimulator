from dataclasses import (
    dataclass,
    field
)

from src.core.program_driven_simulator import (
    ProgramDrivenSimulator
)

from src.analysis.material_consult_generator import (
    MaterialConsultGenerator
)

from src.analysis.collision_consult_generator import (
    CollisionConsultGenerator
)
from src.analysis.manipulator_separation_report import (
    ManipulatorSeparationReport
)


@dataclass
class IterativeConsultResolutionResult:

    consults: list = field(
        default_factory=list
    )

    simulation_result: object | None = None

    iterations: int = 0

    stopped_reason: str = ""

    skipped_consults: list = field(
        default_factory=list
    )


class IterativeConsultResolver:

    def __init__(
        self,
        configuration,
        programs,
        cycles,
        initial_station_occupancy=None,
        initial_manipulator_positions=None,
        max_iterations=40,
        include_material_consults=True
    ):
        self.configuration = (
            configuration
        )

        self.programs = (
            programs
            or
            {}
        )

        self.cycles = int(
            cycles
        )

        self.initial_station_occupancy = (
            initial_station_occupancy
        )
        self.initial_manipulator_positions = (
            initial_manipulator_positions
        )

        self.max_iterations = int(
            max_iterations
        )

        self.include_material_consults = bool(
            include_material_consults
        )

        self.skipped_consults = []

    def resolve(
        self
    ):
        consults = []

        if self.include_material_consults:
            material_consults = (
                MaterialConsultGenerator(
                    programs=(
                        self.programs
                    ),
                    initial_station_occupancy=(
                        self.initial_station_occupancy
                    ),
                    load_station=(
                        self._load_station()
                    ),
                    unload_station=(
                        self._unload_station()
                    )
                ).generate()
            )

            for consult in material_consults:
                self._safe_add_consult(
                    consults,
                    consult
                )

        simulation_result = None

        for iteration in range(
            self.max_iterations
            +
            1
        ):
            simulation_result = (
                self._simulate(
                    consults
                )
            )

            if self._is_clean(
                simulation_result
            ):
                return IterativeConsultResolutionResult(
                    consults=(
                        consults
                    ),
                    simulation_result=(
                        simulation_result
                    ),
                    iterations=(
                        iteration
                    ),
                    stopped_reason=(
                        "OK"
                    ),
                    skipped_consults=(
                        self.skipped_consults
                    )
                )

            if (
                iteration
                >=
                self.max_iterations
            ):
                return IterativeConsultResolutionResult(
                    consults=(
                        consults
                    ),
                    simulation_result=(
                        simulation_result
                    ),
                    iterations=(
                        iteration
                    ),
                    stopped_reason=(
                        "MAX_ITERATIONS"
                    ),
                    skipped_consults=(
                        self.skipped_consults
                    )
                )

            collision_consults = (
                CollisionConsultGenerator(
                    programs=(
                        self.programs
                    ),
                    simulation_result=(
                        simulation_result
                    ),
                    configuration=(
                        self.configuration
                    )
                ).generate()
            )

            added = False

            for consult in collision_consults:
                if self._safe_add_consult(
                    consults,
                    consult
                ):
                    added = True

            if not added:
                return IterativeConsultResolutionResult(
                    consults=(
                        consults
                    ),
                    simulation_result=(
                        simulation_result
                    ),
                    iterations=(
                        iteration
                    ),
                    stopped_reason=(
                        "NO_NEW_CONSULT"
                    ),
                    skipped_consults=(
                        self.skipped_consults
                    )
                )

        return IterativeConsultResolutionResult(
            consults=(
                consults
            ),
            simulation_result=(
                simulation_result
            ),
            iterations=(
                self.max_iterations
            ),
            stopped_reason=(
                "UNKNOWN"
            ),
            skipped_consults=(
                self.skipped_consults
            )
        )

    def _route(
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
                    station.id
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
                station.id
            )

        return route

    def _load_station(
        self
    ):
        route = (
            self._route()
        )

        if not route:
            return None

        return (
            route[
                0
            ]
        )

    def _unload_station(
        self
    ):
        route = (
            self._route()
        )

        if not route:
            return None

        return (
            route[
                -1
            ]
        )

    def _simulate(
        self,
        consults
    ):
        simulator = ProgramDrivenSimulator(
            configuration=(
                self.configuration
            ),
            programs=(
                self.programs
            ),
            consults=(
                consults
            ),
            cycles=(
                self.cycles
            ),
            initial_station_occupancy=(
                self.initial_station_occupancy
            ),
            initial_manipulator_positions=(
                self.initial_manipulator_positions
                )
        )

        return simulator.run()

    def _is_clean(
        self,
        result
    ):
        if result is None:
            return False

        empty_pickup = len(
            getattr(
                result,
                "empty_pickup_warnings",
                []
            )
        )

        occupied_drop = len(
            getattr(
                result,
                "occupied_drop_warnings",
                []
            )
        )

        if (
            empty_pickup
            >
            0
            or
            occupied_drop
            >
            0
        ):
            return False

        separation = (
            ManipulatorSeparationReport()
            .analyze(
                result,
                self.configuration
            )
        )

        if (
            separation is not None
            and
            bool(
                getattr(
                    separation,
                    "collision",
                    False
                )
            )
        ):
            print(
                "ITERATIVE CONSULT DETECTED COLLISION "
                f"M{separation.manipulator_a}/M{separation.manipulator_b} "
                f"t={separation.time:.1f}s "
                f"pos={separation.position_a:.2f}/"
                f"{separation.position_b:.2f} "
                f"d={separation.minimum_distance:.2f} "
                f"segments={separation.segment_a_type}/"
                f"{separation.segment_b_type}"
            )

            return False

        return True

    def _consult_key(
        self,
        consult
    ):
        return (
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

    def _safe_add_consult(
        self,
        consults,
        consult
    ):
        key = (
            self._consult_key(
                consult
            )
        )

        for existing in consults:
            if (
                self._consult_key(
                    existing
                )
                ==
                key
            ):
                return False

        candidate = (
            consults
            +
            [
                consult
            ]
        )

        if self._has_dependency_cycle(
            candidate
        ):
            self.skipped_consults.append(
                consult
            )

            print(
                f"SKIP CONSULT CYCLE "
                f"{consult.to_text()}"
            )

            return False

        consults.append(
            consult
        )

        print(
            f"ADD CONSULT "
            f"{consult.to_text()}"
        )

        return True

    def _max_plc_index_for_program(
        self,
        program
    ):
        return (
            len(
                getattr(
                    program,
                    "steps",
                    []
                )
            )
            *
            3
        )

    def _dependency_graph(
        self,
        consults
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
                    int(
                        manipulator_id
                    ),
                    int(
                        plc_index
                    )
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
                        int(
                            manipulator_id
                        ),
                        int(
                            plc_index
                            +
                            1
                        )
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

        for consult in consults:
            prerequisite = (
                int(
                    consult.target_manipulator_id
                ),
                int(
                    consult.target_plc_index
                )
            )

            blocked = (
                int(
                    consult.source_manipulator_id
                ),
                int(
                    consult.source_plc_index
                )
            )

            if prerequisite not in graph:
                graph[
                    prerequisite
                ] = set()

            if blocked not in graph:
                graph[
                    blocked
                ] = set()

            graph[
                prerequisite
            ].add(
                blocked
            )

        return graph

    def _has_dependency_cycle(
        self,
        consults
    ):
        graph = (
            self._dependency_graph(
                consults
            )
        )

        visited = set()
        stack = set()

        def visit(
            node
        ):
            if node in stack:
                return True

            if node in visited:
                return False

            visited.add(
                node
            )

            stack.add(
                node
            )

            for next_node in graph.get(
                node,
                set()
            ):
                if visit(
                    next_node
                ):
                    return True

            stack.remove(
                node
            )

            return False

        for node in graph.keys():
            if visit(
                node
            ):
                return True

        return False