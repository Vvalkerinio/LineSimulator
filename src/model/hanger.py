from dataclasses import dataclass


@dataclass
class Hanger:

    id: int
    current_station: int
    route: list[int]

    route_index: int = 0
    entered_station_at: float = 0.0

    def next_station(self):

        if self.route_index + 1 >= len(
            self.route
        ):
            return None

        return self.route[
            self.route_index + 1
        ]

    def advance(self):

        if self.next_station() is None:
            return

        self.route_index += 1

        self.current_station = (
            self.route[
                self.route_index
            ]
        )

    def is_finished(self):

        return (
            self.route_index
            >= len(self.route) - 1
        )