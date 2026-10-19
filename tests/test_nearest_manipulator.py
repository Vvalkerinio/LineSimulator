from src.model.manipulator import (
    Manipulator
)


def test_pickup_time_depends_on_position():

    m1 = Manipulator(
        id=1,
        position=1,
        lift_time=1,
        drop_time=1,
        travel_time_per_position=1
    )

    m4 = Manipulator(
        id=4,
        position=22,
        lift_time=1,
        drop_time=1,
        travel_time_per_position=1
    )

    assert (
        m4.pickup_travel_time(20)
        <
        m1.pickup_travel_time(20)
    )