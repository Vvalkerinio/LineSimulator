import pytest

from types import SimpleNamespace

from src.core.program_track_guard import ProgramTrackGuard


def make_service(mode="off", conflict=None, idle_calls=None):
    configuration = SimpleNamespace(
        program_driven_track_guard_mode=mode
    )
    idle_calls = idle_calls if idle_calls is not None else []
    return ProgramTrackGuard(
        configuration=configuration,
        conflict_finder=lambda **kwargs: conflict,
        idle_appender=lambda **kwargs: idle_calls.append(kwargs),
        logical_step_resolver=lambda plc_index: (plc_index - 1) // 3 + 1,
        wait_epsilon=0.1,
        max_iterations=2
    ), idle_calls


def runtime():
    return SimpleNamespace(
        manipulator_id=2,
        current_plc_index=7
    )


def conflict():
    return {
        "other_manipulator_id": 3,
        "other_start_time": 10.0,
        "other_end_time": 20.0,
        "other_start_position": 9.0,
        "other_end_position": 12.0,
        "distance": 1.0,
        "minimum_spacing": 2.0,
        "conflict_end_time": 20.0
    }


def state():
    return {
        "track_waits": [],
        "track_guard_events": []
    }


def test_off_does_not_call_conflict_finder_or_change_time():
    called = []
    service = ProgramTrackGuard(
        configuration=SimpleNamespace(),
        conflict_finder=lambda **kwargs: called.append(kwargs),
        idle_appender=lambda **kwargs: None,
        logical_step_resolver=lambda index: 1
    )
    assert service.apply(None, state(), runtime(), 10.0, 15.0, 8, 14) == (10.0, 15.0)
    assert called == []


def test_warn_records_conflict_without_waiting():
    service, idle_calls = make_service("warn", conflict())
    target_state = state()
    assert service.apply(None, target_state, runtime(), 10.0, 15.0, 8, 14) == (10.0, 15.0)
    assert idle_calls == []
    assert target_state["track_waits"] == []
    assert len(target_state["track_guard_events"]) == 1
    assert target_state["track_guard_events"][0]["plc_index"] == 7


def test_enforce_adds_wait_then_rechecks_until_clear():
    responses = [conflict(), None]
    idle_calls = []
    service = ProgramTrackGuard(
        configuration=SimpleNamespace(program_driven_track_guard_mode="enforce"),
        conflict_finder=lambda **kwargs: responses.pop(0),
        idle_appender=lambda **kwargs: idle_calls.append(kwargs),
        logical_step_resolver=lambda index: 3,
        wait_epsilon=0.1
    )
    target_state = state()
    new_start, new_end = service.apply(
        None, target_state, runtime(), 10.0, 15.0, 8, 14
    )
    assert new_start == 20.1
    assert new_end == 25.1
    assert len(idle_calls) == 1
    assert len(target_state["track_waits"]) == 1
    assert target_state["track_waits"][0]["wait_time"] == pytest.approx(10.1)
