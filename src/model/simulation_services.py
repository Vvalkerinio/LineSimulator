from dataclasses import dataclass


@dataclass
class SimulationServices:

    transport_scheduler: object | None = None

    manipulator_manager: object | None = None

    availability: object | None = None

    track_service: object | None = None

    trajectory_manager: object | None = None