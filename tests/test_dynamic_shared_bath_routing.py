from src.model.station import Station
from src.model.bath_group import (
    BathGroup
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


def test_dynamic_bath_group_selection():

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

    decision = (
        RoutingEngine(
            manager,
            registry
        )
        .select_bath_group(
            "KTL_1"
        )
    )

    assert (
        decision.selected_station
        == 10
    )