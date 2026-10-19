from src.model.queue_delay_info import (
    QueueDelayInfo
)

from src.model.waiting_transport import (
    WaitingTransport
)


class DeadlockDetector:

    def __init__(
        self,
        max_wait_time: float
    ):
        self.max_wait_time = (
            max_wait_time
        )

    def detect(
        self,
        current_time: float,
        station_id: int,
        transport: WaitingTransport
    ):

        waiting_time = (
            current_time
            - transport.requested_at
        )

        if (
            waiting_time
            <= self.max_wait_time
        ):
            return None

        #
        # To NIE jest deadlock.
        # To tylko długa kolejka.
        #
        return QueueDelayInfo(
            station_id=
                station_id,

            hanger_id=
                transport.hanger_id,

            waiting_time=
                waiting_time,

            detected_at=
                current_time
        )