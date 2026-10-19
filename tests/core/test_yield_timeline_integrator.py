from src.core.event_track_yield_planner import EventTrackYieldMove
from src.core.yield_timeline_integrator import YieldTimelineIntegrator
from src.model.manipulator_timeline_segment import ManipulatorTimelineSegment


def test_yield_splits_stale_idle_and_updates_position_after_move():
    idle = ManipulatorTimelineSegment(3, 723.5, 987.0, 15, 15, "idle")
    move = EventTrackYieldMove(3, 2, 15, 16, 907.5, 912.0, 14)
    result = YieldTimelineIntegrator().integrate([idle], [move])
    assert [(x.segment_type, x.start_time, x.end_time, x.start_position, x.end_position) for x in result] == [
        ("idle", 723.5, 907.5, 15.0, 15.0),
        ("event_track_yield", 907.5, 912.0, 15.0, 16.0),
        ("idle", 912.0, 987.0, 16.0, 16.0),
    ]


def test_multiple_yields_do_not_leave_overlapping_idle_segments():
    idle = ManipulatorTimelineSegment(3, 700.0, 1400.0, 15, 15, "idle")
    moves = [
        EventTrackYieldMove(3, 2, 15, 16, 900.0, 905.0, 14),
        EventTrackYieldMove(3, 2, 15, 16, 1200.0, 1205.0, 14),
    ]
    result = YieldTimelineIntegrator().integrate([idle], moves)
    yields = [x for x in result if x.segment_type == "event_track_yield"]
    assert len(yields) == 2
    for i, left in enumerate(result):
        for right in result[i+1:]:
            if left.manipulator_id == right.manipulator_id:
                assert left.end_time <= right.start_time or right.end_time <= left.start_time
