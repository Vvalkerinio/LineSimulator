from src.model.project import Project
from src.model.bath_group import (
    BathGroup
)

from src.model.simulation_configuration import (
    SimulationConfiguration
)


def test_find_bath_group():

    project = Project(
        name="TEST",
        configuration=
            SimulationConfiguration(
                stations=[],
                manipulators=[]
            )
    )

    project.add_bath_group(
        BathGroup(
            id="KTL_1",
            name="Shared Bath",
            stations=[9, 10]
        )
    )

    group = project.get_bath_group(
        "KTL_1"
    )

    assert group.stations == [9, 10]
