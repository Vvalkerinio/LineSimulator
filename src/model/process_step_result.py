from dataclasses import dataclass


@dataclass
class ProcessStepResult:

    step_id: str

    available_stations: list[int]