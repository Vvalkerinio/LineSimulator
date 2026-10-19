from src.core.hanger_factory import (
    HangerFactory
)


def test_hanger_generation():

    hangers = (
        HangerFactory()
        .create(
            hanger_count=3,
            route=[1, 2, 3],
            entry_interval=60
        )
    )

    assert len(hangers) == 3

    assert (
        hangers[0].id
        == 1
    )

    assert (
        hangers[1].entered_station_at
        == 60
    )

    assert (
        hangers[2].entered_station_at
        == 120
    )