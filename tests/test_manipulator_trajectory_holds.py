from types import SimpleNamespace

from src.gui.manipulator_trajectory_tab import ManipulatorTrajectoryTab


def _segment(start_time, end_time, end_position):
    return SimpleNamespace(
        start_time=start_time,
        end_time=end_time,
        end_position=end_position
    )


def test_trajectory_hold_intervals_fill_initial_internal_and_final_gaps():
    segments = [
        _segment(7, 8, 3),
        _segment(2, 4, 2)
    ]

    intervals = ManipulatorTrajectoryTab._trajectory_hold_intervals(
        segments,
        0,
        10,
        0
    )

    assert intervals == [
        (0.0, 2.0, 0.0),
        (4.0, 7.0, 2.0),
        (8.0, 10.0, 3.0)
    ]


def test_trajectory_hold_intervals_clip_to_visible_window():
    segments = [
        _segment(2, 4, 2),
        _segment(6, 8, 3)
    ]

    intervals = ManipulatorTrajectoryTab._trajectory_hold_intervals(
        segments,
        5,
        7,
        2
    )

    assert intervals == [
        (5.0, 6.0, 2.0)
    ]
