from pathlib import Path

from src.model.station import Station
from src.model.manipulator import (
    Manipulator
)

from src.model.bath_group import (
    BathGroup
)

from src.model.project import (
    Project
)

from src.model.simulation_configuration import (
    SimulationConfiguration
)

from src.core.project_repository import (
    ProjectRepository
)


def test_project_save(tmp_path):

    config = SimulationConfiguration(
        stations=[
            Station(
                id=1,
                name="P1",
                enabled=True,
                min_process_time=10,
                max_process_time=100
            )
        ],
        manipulators=[
            Manipulator(
                id=1,
                position=1,
                lift_time=3,
                drop_time=3,
                travel_time_per_position=2
            )
        ]
    )

    project = Project(
        name="TEST_PROJECT",
        configuration=config
    )

    project.add_bath_group(
        BathGroup(
            id="KTL_1",
            name="Shared Bath",
            stations=[9, 10]
        )
    )

    file_path = (
        tmp_path / "project.json"
    )

    repository = ProjectRepository()

    repository.save(
        project,
        str(file_path)
    )

    assert file_path.exists()