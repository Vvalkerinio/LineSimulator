from src.model.transport_request import TransportRequest


class Scheduler:

    def __init__(
        self,
        station_manager,
        hanger_manager,
        transport_manager
    ):
        self.station_manager = station_manager
        self.hanger_manager = hanger_manager
        self.transport_manager = transport_manager

    def collect_requests(
        self,
        current_time: float
    ):

        requests = []

        for hanger in self.hanger_manager.all():

            if hanger.is_finished():
                continue

            if self.transport_manager.has_pending(
                hanger.id
            ):
                continue

            station = self.station_manager.station(
                hanger.current_station
            )

            residence = (
                current_time
                - hanger.entered_station_at
            )

            if (
                residence
                < station.min_process_time
            ):
                continue

            target = hanger.next_station()

            if target is None:
                continue

            if not self.station_manager.is_free(
                target
            ):
                continue

            slack = (
                station.max_process_time
                - residence
            )

            requests.append(
                (
                    slack,
                    TransportRequest(
                        hanger_id=hanger.id,
                        source_station=hanger.current_station,
                        target_station=target,
                        ready_at=current_time
                    )
                )
            )

        requests.sort(
            key=lambda item: item[0]
        )

        return [
            item[1]
            for item in requests
        ]