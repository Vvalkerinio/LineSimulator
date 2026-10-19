from src.analysis.iterative_consult_resolver import (
    IterativeConsultResolver
)


class ConsultPipeline:

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
        )

        self.cycles = (
            cycles
        )

        self.initial_station_occupancy = (
            initial_station_occupancy
        )

        self.initial_manipulator_positions = (
            initial_manipulator_positions
        )

        self.max_iterations = (
            max_iterations
        )

        self.include_material_consults = (
            include_material_consults
        )

    def generate(
        self
    ):
        return (
            IterativeConsultResolver(
                configuration=(
                    self.configuration
                ),
                programs=(
                    self.programs
                ),
                cycles=(
                    self.cycles
                ),
                initial_station_occupancy=(
                    self.initial_station_occupancy
                ),
                initial_manipulator_positions=(
                    self.initial_manipulator_positions
                ),
                max_iterations=(
                    self.max_iterations
                ),
                include_material_consults=(
                    self.include_material_consults
                )
            ).resolve()
        )