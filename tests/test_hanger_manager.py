from src.core.hanger_manager import (
    HangerManager
)

from src.model.hanger import (
    Hanger
)


def test_hanger_move():

    manager = HangerManager()

    hanger = Hanger(
        id=1,
        current_station=1,
        route=[1, 2, 3]
    )

    manager.add_hanger(
        hanger
    )

    manager.move(
        hanger_id=1,
        current_time=10
    )

    assert (
        manager.get(1).current_station
        == 2
    )