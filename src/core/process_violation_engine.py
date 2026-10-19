from src.model.process_violation import (
    ProcessViolation
)


class ProcessViolationEngine:

    def validate(
        self,
        station,
        actual_time: float
    ):

        if (
            actual_time
            <= station.max_process_time
        ):
            return None

        return ProcessViolation(
            station_id=station.id,
            station_name=station.name,
            required_time=actual_time,
            max_allowed_time=station.max_process_time
        )