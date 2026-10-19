from src.model.manipulator_assignment import (
    ManipulatorAssignment
)


def test_assignment_creation():

    assignment = (
        ManipulatorAssignment(
            manipulator_id=1,
            source_station=1,
            target_station=5,
            start_time=0,
            finish_time=10
        )
    )

    assert (
        assignment.target_station
        == 5
    )
