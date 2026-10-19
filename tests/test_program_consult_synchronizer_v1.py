import pytest

from types import SimpleNamespace

from src.core.program_consult_synchronizer import (
    ProgramConsultSynchronizer
)


def consult(source_m=1, source_index=7, target_m=2, target_index=15):
    return SimpleNamespace(
        source_manipulator_id=source_m,
        source_plc_index=source_index,
        target_manipulator_id=target_m,
        target_plc_index=target_index
    )


def runtime(manipulator_id=1, index=7, time=10.0):
    return SimpleNamespace(
        manipulator_id=manipulator_id,
        current_plc_index=index,
        cycle_no=2,
        current_position=8,
        available_time=time,
        completed_indices={}
    )


def state():
    return {"consult_waits": [], "active_consult_waits": {}}


def test_indexes_and_finds_only_matching_blocking_consult():
    target = ProgramConsultSynchronizer(
        [consult()],
        completed_target_resolver=lambda **kwargs: False,
        target_time_resolver=lambda *args: None
    )
    blocked = target.blocking_consult(runtime(), {2: runtime(2, 15)})
    assert blocked[0] == 1
    assert blocked[1].target_plc_index == 15
    assert target.blocking_consult(runtime(index=10), {}) is None


def test_wait_record_contains_requested_label_and_duration():
    source = runtime()
    target_runtime = runtime(2, 15, 20.0)
    target = ProgramConsultSynchronizer(
        [consult()],
        completed_target_resolver=lambda **kwargs: False,
        target_time_resolver=lambda *args: None,
        recheck_interval=0.1
    )
    target_state = state()
    assert target.evaluate(target_state, source, {2: target_runtime}) is not None
    assert source.available_time == 20.1

    target.completed_target_resolver = lambda **kwargs: True
    assert target.evaluate(target_state, source, {2: target_runtime}) is None
    record = target_state["consult_waits"][0]
    assert record["label"] == "M2:15"
    assert record["source_plc_index"] == 7
    assert record["position"] == 8.0
    assert record["duration"] == pytest.approx(10.1)


def test_completed_consult_does_not_create_wait():
    target = ProgramConsultSynchronizer(
        [consult()],
        completed_target_resolver=lambda **kwargs: True,
        target_time_resolver=lambda *args: None
    )
    target_state = state()
    assert target.evaluate(target_state, runtime(), {}) is None
    assert target_state["consult_waits"] == []
