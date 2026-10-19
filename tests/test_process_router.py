from src.model.station import Station
from src.model.bath_group import (
    BathGroup
)
from src.model.recipe_step import (
    RecipeStep
)

from src.core.station_manager import (
    StationManager
)
from src.core.routing_engine import (
    RoutingEngine
)
from src.core.bath_group_registry import (
    BathGroupRegistry
)
from src.core.recipe_resolver import (
    RecipeResolver
)
from src.core.process_router import (
    ProcessRouter
)


def test_process_router_shared_bath():

    manager = StationManager(
        [
            Station(
                id=9,
                name="KTL_A",
                enabled=True,
                min_process_time=10,
                max_process_time=300,
                shared_bath_group="KTL_1"
            ),
            Station(
                id=10,
                name="KTL_B",
                enabled=True,
                min_process_time=10,
                max_process_time=300,
                shared_bath_group="KTL_1"
            )
        ]
    )

    manager.occupy(
        station_id=9,
        hanger_id=1,
        current_time=0
    )

    registry = (
        BathGroupRegistry()
    )

    registry.add(
        BathGroup(
            id="KTL_1",
            name="Shared Bath",
            stations=[9, 10]
        )
    )

    step = RecipeStep(
        id="KTL_1",
        name="Shared Bath",
        min_time=10,
        max_time=300,
        bath_group_id="KTL_1"
    )

    router = ProcessRouter(
        RecipeResolver(registry),
        RoutingEngine(manager)
    )

    station = (
        router.resolve_target_station(
            step
        )
    )

    assert station == 10
