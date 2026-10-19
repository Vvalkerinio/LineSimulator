import pytest

from src.core.segment_builder import SegmentBuilder


def test_fractional_forward_position_is_bounded_and_preserves_time():
    segments = SegmentBuilder().build(1, 3.7, 5.0, 10.0, 4.3)
    assert len(segments) == 2
    assert (segments[0].segment_start, segments[0].segment_end) == pytest.approx((3.7, 4.0))
    assert (segments[1].segment_start, segments[1].segment_end) == pytest.approx((4.0, 5.0))
    assert segments[-1].end_time == pytest.approx(10.0 + 1.3 * 4.3)


def test_fractional_reverse_position_is_bounded_and_preserves_time():
    segments = SegmentBuilder().build(1, 5.0, 3.7, 2.0, 4.3)
    assert len(segments) == 2
    assert (segments[0].segment_start, segments[0].segment_end) == pytest.approx((4.0, 5.0))
    assert (segments[1].segment_start, segments[1].segment_end) == pytest.approx((3.7, 4.0))
    assert segments[-1].end_time == pytest.approx(2.0 + 1.3 * 4.3)


def test_near_integer_float_is_normalized_instead_of_overshooting_forever():
    segments = SegmentBuilder().build(1, 3.9999999999999996, 5, 0, 4.3)
    assert len(segments) == 1
    assert segments[0].segment_start == pytest.approx(4.0)
    assert segments[0].segment_end == pytest.approx(5.0)
    assert segments[0].end_time == pytest.approx(4.3)


def test_zero_distance_has_no_reservations():
    assert SegmentBuilder().build(1, 4.0, 4.0, 12.0, 4.3) == []
