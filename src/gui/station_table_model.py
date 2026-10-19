from src.model.station import (
    Station
)


class StationTableModel:

    def __init__(
        self,
        stations: list[Station]
    ):
        self.stations = (
            stations
        )

    def row_count(
        self
    ) -> int:

        return len(
            self.stations
        )

    def station(
        self,
        index: int
    ) -> Station:

        return (
            self.stations[
                index
            ]
        )

    def update_station(
        self,
        row: int,
        name: str,
        enabled: bool,
        min_time: float,
        max_time: float,
        shared_bath: str
    ) -> None:

        station = (
            self.stations[
                row
            ]
        )

        station.name = (
            name
        )

        station.enabled = (
            enabled
        )

        station.min_process_time = (
            min_time
        )

        station.max_process_time = (
            max_time
        )

        if hasattr(
            station,
            "shared_bath_group"
        ):

            station.shared_bath_group = (
                shared_bath
            )