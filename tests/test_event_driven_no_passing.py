from src.core.event_driven_passing_detector import (
    EventDrivenPassingDetector
)


class FakeTrajectory:

    def position_at(
        self,
        manipulator_id,
        time
    ):
        if manipulator_id == 1:
            return 5

        return 5


class FakeManipulator:

    def __init__(
        self,
        ident
    ):
        self.id = ident


class FakeManager:

    def all(
        self
    ):
        return [
            FakeManipulator(1),
            FakeManipulator(2)
        ]


def test_crossing_rejected():

    detector = (
        EventDrivenPassingDetector(
            FakeTrajectory(),
            FakeManager()
        )
    )

    allowed = (
        detector.transport_allowed(
            manipulator_id=1,
            start_position=1,
            target_position=10,
            start_time=0,
            finish_time=10
        )
    )

    assert allowed is False