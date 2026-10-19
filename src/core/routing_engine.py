from src.model.routing_decision import (
    RoutingDecision
)


class RoutingEngine:

    def __init__(
        self,
        station_manager,
        bath_group_registry=None
    ):
        self.station_manager = (
            station_manager
        )

        self.bath_group_registry = (
            bath_group_registry
        )

    def select_station(
        self,
        candidate_stations: list[int]
    ) -> RoutingDecision:

        free_stations = []

        for station_id in candidate_stations:

            station = (
                self.station_manager.station(
                    station_id
                )
            )

            if not station.enabled:
                continue

            if self.station_manager.is_free(
                station_id
            ):
                free_stations.append(
                    station_id
                )

        if free_stations:

            return RoutingDecision(
                selected_station=
                    free_stations[0],
                reason="FIRST_FREE",
                candidate_stations=
                    free_stations
            )

        active_stations = []

        for station_id in candidate_stations:

            station = (
                self.station_manager.station(
                    station_id
                )
            )

            if station.enabled:
                active_stations.append(
                    station_id
                )

        if active_stations:

            return RoutingDecision(
                selected_station=
                    active_stations[0],
                reason="FALLBACK",
                candidate_stations=
                    active_stations
            )

        return RoutingDecision(
            selected_station=None,
            reason="NO_ACTIVE_STATION",
            candidate_stations=[]
        )

    def select_bath_group(
        self,
        group_id: str
    ) -> RoutingDecision:

        if (
            self.bath_group_registry
            is None
        ):
            raise RuntimeError(
                "BathGroupRegistry not configured"
            )

        group = (
            self.bath_group_registry.get(
                group_id
            )
        )

        return self.select_station(
            group.stations
        )