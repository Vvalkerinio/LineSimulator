from dataclasses import dataclass


@dataclass
class ManipulatorPositionSample:

    manipulator_id: int

    time: float

    position: float