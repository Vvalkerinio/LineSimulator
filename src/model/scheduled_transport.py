from dataclasses import dataclass


@dataclass(init=False)
class ScheduledTransport:

    hanger_id: int

    source_station: int

    target_station: int

    manipulator_id: int

    pickup_start_time: float
    pickup_finish_time: float

    transport_start_time: float
    transport_finish_time: float

    return_position: int
    return_start_time: float
    return_finish_time: float

    def __init__(
        self,
        hanger_id: int,
        source_station: int,
        target_station: int,
        manipulator_id: int,
        pickup_start_time=None,
        pickup_finish_time=None,
        transport_start_time=None,
        transport_finish_time=None,
        return_position=None,
        return_start_time=None,
        return_finish_time=None,
        start_time=None,
        finish_time=None
    ):

        self.hanger_id = (
            hanger_id
        )

        self.source_station = (
            source_station
        )

        self.target_station = (
            target_station
        )

        self.manipulator_id = (
            manipulator_id
        )

        if (
            start_time is not None
            and
            finish_time is not None
        ):

            self.pickup_start_time = (
                start_time
            )

            self.pickup_finish_time = (
                start_time
            )

            self.transport_start_time = (
                start_time
            )

            self.transport_finish_time = (
                finish_time
            )

            self.return_position = (
                source_station
            )

            self.return_start_time = (
                finish_time
            )

            self.return_finish_time = (
                finish_time
            )

        else:

            self.pickup_start_time = (
                pickup_start_time
            )

            self.pickup_finish_time = (
                pickup_finish_time
            )

            self.transport_start_time = (
                transport_start_time
            )

            self.transport_finish_time = (
                transport_finish_time
            )

            self.return_position = (
                return_position
                if return_position is not None
                else source_station
            )

            self.return_start_time = (
                return_start_time
                if return_start_time is not None
                else transport_finish_time
            )

            self.return_finish_time = (
                return_finish_time
                if return_finish_time is not None
                else transport_finish_time
            )

    @property
    def start_time(
        self
    ) -> float:

        return (
            self.pickup_start_time
        )

    @property
    def finish_time(
        self
    ) -> float:

        return (
            self.return_finish_time
        )