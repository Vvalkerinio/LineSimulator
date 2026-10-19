from src.model.simulation_result import (
    SimulationResult
)

from src.model.manipulator_task import (
    ManipulatorTask
)


def test_result_contains_tasks():

    result = SimulationResult()

    result.manipulator_tasks.append(
        ManipulatorTask(
            manipulator_id=1,
            hanger_id=1,
            source_station=1,
            target_station=2,
            start_time=0,
            end_time=10
        )
    )

    assert (
        len(
            result.manipulator_tasks
        )
        == 1
    )