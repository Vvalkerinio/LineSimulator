class ProcessTimeEngine:

    def process_time(
        self,
        station
    ) -> float:

        return (
            station.min_process_time
        )

    def actual_time(
        self,
        station
    ) -> float:

        return (
            station.min_process_time
        )