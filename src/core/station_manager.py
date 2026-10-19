from src.model.station import (
    Station
)

from src.model.station_state import (
    StationState
)


class StationManager:

    def __init__(
        self,
        stations: list[Station]
    ) -> None:

        self._stations = {
            station.id: station
            for station in stations
        }

        self._states = {
            station.id: StationState(
                station_id=
                    station.id
            )
            for station in stations
        }

    def station(
        self,
        station_id: int
    ) -> Station:

        return (
            self._stations[
                station_id
            ]
        )

    def state(
        self,
        station_id: int
    ) -> StationState:

        return (
            self._states[
                station_id
            ]
        )

    def is_free(
        self,
        station_id: int,
        current_time: float | None = None
    ) -> bool:

        #
        # 11.9.2 Physical Station Occupancy
        #
        # Nie zwalniamy stanowiska automatycznie
        # po upływie occupied_until.
        #
        # occupied_until oznacza:
        # "proces technologiczny zakończony"
        #
        # a NIE:
        # "stanowisko fizycznie puste".
        #
        state = (
            self.state(
                station_id
            )
        )

        return (
            state.hanger_id
            is None
        )

    def is_available(
        self,
        station_id: int,
        current_time: float
    ) -> bool:

        return (
            self.is_free(
                station_id,
                current_time
            )
        )

    def is_process_finished(
        self,
        station_id: int,
        current_time: float
    ) -> bool:

        state = (
            self.state(
                station_id
            )
        )

        if (
            state.hanger_id
            is None
        ):
            return False

        return (
            current_time
            >= state.occupied_until
        )

    def occupy(
        self,
        station_id: int,
        hanger_id: int,
        current_time: float | None = None,
        occupied_until: float | None = None
    ) -> None:

        state = (
            self.state(
                station_id
            )
        )

        state.occupied = True

        state.hanger_id = (
            hanger_id
        )

        if occupied_until is not None:

            state.occupied_until = (
                occupied_until
            )

        elif current_time is not None:

            state.occupied_until = (
                current_time
            )

        else:

            state.occupied_until = 0.0

    def release(
        self,
        station_id: int
    ) -> None:

        state = (
            self.state(
                station_id
            )
        )

        state.occupied = False

        state.hanger_id = None

        state.occupied_until = 0.0