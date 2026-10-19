from types import SimpleNamespace

import pytest

from src.core.program_track_conflict_detector import (
    ProgramTrackConflictDetector
)


def detector(spacing=2.0):
    return ProgramTrackConflictDetector(
        SimpleNamespace(minimum_manipulator_spacing=spacing)
    )


def segment(manipulator_id, start, end, p0, p1):
    return SimpleNamespace(
        manipulator_id=manipulator_id,
        start_time=start,
        end_time=end,
        start_position=p0,
        end_position=p1
    )


def test_position_interpolates_and_clamps():
    value = detector().position_on_segment(10, 20, 5, 15, 15)
    assert value == pytest.approx(10.0)
    assert detector().position_on_segment(10, 20, 5, 15, 0) == 5.0
    assert detector().position_on_segment(10, 20, 5, 15, 30) == 15.0


def test_minimum_distance_detects_crossing():
    distance = detector().minimum_distance(
        0, 10, 0, 10,
        0, 10, 10, 0
    )
    assert distance == pytest.approx(0.0)


def test_minimum_distance_returns_none_without_time_overlap():
    assert detector().minimum_distance(
        0, 5, 0, 1,
        6, 10, 2, 3
    ) is None


def test_find_conflict_uses_latest_conflicting_segment_end():
    result = SimpleNamespace(timeline_segments=[
        segment(3, 0, 8, 6, 6),
        segment(4, 2, 12, 7, 7),
        segment(2, 0, 20, 0, 20)
    ])
    runtime = SimpleNamespace(manipulator_id=2)

    conflict = detector(spacing=2.0).find_conflict(
        result=result,
        runtime=runtime,
        start_time=0,
        end_time=10,
        source_position=5,
        target_position=10
    )

    assert conflict is not None
    assert conflict["other_manipulator_id"] == 4
    assert conflict["conflict_end_time"] == 12.0
    assert conflict["minimum_spacing"] == 2.0


def test_spatially_distant_segment_is_rejected_before_exact_distance(monkeypatch):
    target = detector(spacing=2.0)
    calls = []
    monkeypatch.setattr(
        target,
        "minimum_distance",
        lambda *args, **kwargs: calls.append((args, kwargs))
    )
    result = SimpleNamespace(timeline_segments=[
        segment(3, 0, 10, 50, 60)
    ])
    runtime = SimpleNamespace(manipulator_id=2)

    conflict = target.find_conflict(
        result=result,
        runtime=runtime,
        start_time=0,
        end_time=10,
        source_position=5,
        target_position=10
    )

    assert conflict is None
    assert calls == []
