from src.model.hanger import (
    Hanger
)


class HangerFactory:

    def create(
        self,
        hanger_count: int,
        route: list[int],
        entry_interval: float = 60.0
    ):

        hangers = []

        for index in range(
            hanger_count
        ):

            hangers.append(
                Hanger(
                    id=index + 1,
                    current_station=
                        route[0],
                    route=
                        route.copy(),
                    entered_station_at=
                        index
                        * entry_interval
                )
            )

        return hangers

    def create_for_duration(
        self,
        route: list[int],
        feed_duration: float,
        entry_interval: float
    ):

        hangers = []

        hanger_id = 1

        current_time = 0.0

        while (
            current_time
            <= feed_duration
        ):

            hangers.append(
                Hanger(
                    id=hanger_id,
                    current_station=
                        route[0],
                    route=
                        route.copy(),
                    entered_station_at=
                        current_time
                )
            )

            current_time += (
                entry_interval
            )

            hanger_id += 1

        return hangers