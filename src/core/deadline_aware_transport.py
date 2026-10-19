class DeadlineAwareTransport:

    def __init__(
        self,
        station_map,
        station_entry_times
    ):
        self.station_map = (
            station_map
        )

        self.station_entry_times = (
            station_entry_times
        )

    def latest_pickup_time(
        self,
        hanger_id,
        station_id
    ):
        station = (
            self.station_map.get(
                station_id
            )
        )

        if station is None:
            return None

        max_process_time = getattr(
            station,
            "max_process_time",
            None
        )

        if (
            max_process_time is None
            or max_process_time <= 0
        ):
            return None

        entry_time = (
            self.station_entry_times.get(
                (
                    hanger_id,
                    station_id
                )
            )
        )

        if entry_time is None:
            return None

        return (
            entry_time
            +
            max_process_time
        )

    def slack_at(
        self,
        hanger_id,
        station_id,
        pickup_finish_time
    ):
        latest = (
            self.latest_pickup_time(
                hanger_id,
                station_id
            )
        )

        if latest is None:
            return None

        return (
            latest
            -
            pickup_finish_time
        )

    def priority_key(
        self,
        hanger_id,
        station_id,
        current_time
    ):
        latest = (
            self.latest_pickup_time(
                hanger_id,
                station_id
            )
        )

        if latest is None:
            return (
                float(
                    "inf"
                ),
                current_time,
                hanger_id
            )

        return (
            latest,
            current_time,
            hanger_id
        )

    def describe(
        self,
        hanger_id,
        station_id,
        current_time
    ):
        latest = (
            self.latest_pickup_time(
                hanger_id,
                station_id
            )
        )

        if latest is None:
            return (
                "deadline=none"
            )

        remaining = (
            latest
            -
            current_time
        )

        return (
            f"deadline={latest:.1f} "
            f"remaining={remaining:.1f}"
        )