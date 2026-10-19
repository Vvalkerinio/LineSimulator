from src.core.segment_builder import (
    SegmentBuilder
)


def test_build_segments():

    reservations = (
        SegmentBuilder()
        .build(
            manipulator_id=1,
            source_station=5,
            target_station=8,
            start_time=0,
            travel_time_per_position=2
        )
    )

    assert len(reservations) == 3

    assert (
        reservations[0].segment_start
        == 5
    )

    assert (
        reservations[0].segment_end
        == 6
    )

    assert (
        reservations[2].segment_start
        == 7
    )

    assert (
        reservations[2].segment_end
        == 8
    )
