from dataclasses import dataclass


@dataclass
class Manipulator:
    id: int

    position: int

    lift_time: float
    drop_time: float

    travel_time_per_position: float

    work_zone_start: int = 1
    work_zone_end: int = 999
    preferred_parking_position: int | None = None

    def __post_init__(self):
        if self.preferred_parking_position is None:
            self.preferred_parking_position = int(self.position)
        else:
            self.preferred_parking_position = int(
                self.preferred_parking_position
            )

    def travel_time(
        self,
        source_station: int,
        target_station: int
    ) -> float:
        return (
            abs(
                target_station
                - source_station
            )
            * self.travel_time_per_position
        )

    def pickup_travel_time(
        self,
        source_station: int
    ) -> float:
        """Czas pustego dojazdu z aktualnej pozycji do źródła."""
        return self.travel_time(
            self.position,
            source_station
        )

    def transport_time(
        self,
        source_station: int,
        target_station: int
    ) -> float:
        return (
            self.travel_time(
                source_station,
                target_station
            )
        )

    def is_station_inside_work_zone(
        self,
        station_id: int
    ) -> bool:
        return (
            self.work_zone_start
            <= station_id
            <= self.work_zone_end
        )

    def is_transport_inside_work_zone(
        self,
        source_station: int,
        target_station: int
    ) -> bool:
        return (
            self.is_station_inside_work_zone(
                source_station
            )
            and
            self.is_station_inside_work_zone(
                target_station
            )
        )
