from src.model.manipulator_task import (
    ManipulatorTask
)


def test_task_duration():

    task = ManipulatorTask(
        manipulator_id=1,
        hanger_id=7,
        source_station=5,
        target_station=8,
        start_time=100,
        end_time=145
    )

    assert (
        task.duration
        == 45
    )