from dataclasses import dataclass


@dataclass
class ManipulatorTask:

    manipulator_id: int

    hanger_id: int

    source_station: int

    target_station: int

    start_time: float

    end_time: float

    wait_time: float = 0.0

    shared_bath: bool = False

    delayed_by_queue: bool = False

    delayed_by_no_passing: bool = False

    @property
    def duration(
        self
    ) -> float:

        return (
            self.end_time
            - self.start_time
        )
