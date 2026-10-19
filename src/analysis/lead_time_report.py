class LeadTimeReport:

    def _event_name(
        self,
        event
    ):
        event_type = getattr(
            event,
            "event_type",
            None
        )

        name = getattr(
            event_type,
            "name",
            None
        )

        if name is not None:
            return name

        return str(
            event_type
        )

    def _collect_times(
        self,
        result
    ):
        entry_times = {}
        exit_times = {}

        for event in getattr(
            result,
            "events",
            []
        ):
            name = (
                self._event_name(
                    event
                )
            )

            if (
                name
                ==
                "HANGER_ENTRY"
            ):
                if (
                    event.hanger_id
                    not in entry_times
                ):
                    entry_times[
                        event.hanger_id
                    ] = event.time

            elif (
                name
                ==
                "HANGER_EXIT"
            ):
                exit_times[
                    event.hanger_id
                ] = event.time

        requested_times = getattr(
            result,
            "hanger_requested_entry_time",
            {}
        )

        actual_times = getattr(
            result,
            "hanger_actual_entry_time",
            {}
        )

        records = []

        for hanger_id, exit_time in exit_times.items():
            entry_time = (
                entry_times.get(
                    hanger_id
                )
            )

            if entry_time is None:
                continue

            system_lead_time = (
                exit_time
                -
                entry_time
            )

            if system_lead_time < 0:
                continue

            requested_entry = (
                requested_times.get(
                    hanger_id
                )
            )

            actual_entry = (
                actual_times.get(
                    hanger_id
                )
            )

            process_lead_time = None
            entry_queue_wait = None

            if actual_entry is not None:
                process_lead_time = (
                    exit_time
                    -
                    actual_entry
                )

            if (
                requested_entry is not None
                and
                actual_entry is not None
            ):
                entry_queue_wait = (
                    actual_entry
                    -
                    requested_entry
                )

            records.append(
                {
                    "hanger_id":
                        hanger_id,

                    "entry_time":
                        entry_time,

                    "exit_time":
                        exit_time,

                    "lead_time":
                        system_lead_time,

                    "system_lead_time":
                        system_lead_time,

                    "process_lead_time":
                        process_lead_time,

                    "entry_queue_wait":
                        entry_queue_wait,

                    "requested_entry":
                        requested_entry,

                    "actual_entry":
                        actual_entry
                }
            )

        return records

    def _average(
        self,
        values
    ):
        clean_values = [
            value
            for value
            in values
            if value is not None
        ]

        if not clean_values:
            return 0.0

        return (
            sum(
                clean_values
            )
            /
            len(
                clean_values
            )
        )

    def _fmt(
        self,
        value
    ):
        if value is None:
            return "-"

        return (
            f"{value:.1f}"
        )

    def calculate(
        self,
        result
    ):
        records = (
            self._collect_times(
                result
            )
        )

        system_lead_times = [
            record[
                "system_lead_time"
            ]
            for record
            in records
        ]

        process_lead_times = [
            record[
                "process_lead_time"
            ]
            for record
            in records
        ]

        entry_wait_times = [
            record[
                "entry_queue_wait"
            ]
            for record
            in records
        ]

        steady_state = getattr(
            result,
            "steady_state",
            None
        )

        steady_start = None

        if isinstance(
            steady_state,
            dict
        ):
            steady_start = (
                steady_state.get(
                    "steady_state_time",
                    None
                )
            )

        steady_records = []

        if steady_start is not None:
            steady_records = [
                record
                for record
                in records
                if (
                    record[
                        "exit_time"
                    ]
                    >= steady_start
                )
            ]

        steady_system_times = [
            record[
                "system_lead_time"
            ]
            for record
            in steady_records
        ]

        clean_entry_wait_times = [
            value
            for value
            in entry_wait_times
            if value is not None
        ]

        summary = {
            "count":
                len(
                    records
                ),

            "average_time":
                self._average(
                    system_lead_times
                ),

            "average_process_time":
                self._average(
                    process_lead_times
                ),

            "average_entry_queue_wait":
                self._average(
                    entry_wait_times
                ),

            "max_entry_queue_wait":
                (
                    max(
                        clean_entry_wait_times
                    )
                    if clean_entry_wait_times
                    else 0.0
                ),

            "min_time":
                (
                    min(
                        system_lead_times
                    )
                    if system_lead_times
                    else 0.0
                ),

            "max_time":
                (
                    max(
                        system_lead_times
                    )
                    if system_lead_times
                    else 0.0
                ),

            "steady_state_count":
                len(
                    steady_records
                ),

            "steady_state_average_time":
                self._average(
                    steady_system_times
                ),

            "steady_state_time":
                steady_start,

            "records":
                records
        }

        result.lead_time_summary = (
            summary
        )

        return summary

    def print_summary(
        self,
        result
    ):
        summary = (
            self.calculate(
                result
            )
        )

        if (
            summary[
                "count"
            ]
            <= 0
        ):
            return

        print()
        print(
            "=" * 60
        )
        print(
            "LOAD TO UNLOAD LEAD TIME REPORT"
        )
        print(
            "=" * 60
        )

        print(
            f"Completed hangers       : "
            f"{summary['count']}"
        )

        print(
            f"Average system lead     : "
            f"{summary['average_time']:.1f}s"
        )

        print(
            f"Average process lead    : "
            f"{summary['average_process_time']:.1f}s"
        )

        print(
            f"Average entry wait      : "
            f"{summary['average_entry_queue_wait']:.1f}s"
        )

        print(
            f"Max entry wait          : "
            f"{summary['max_entry_queue_wait']:.1f}s"
        )

        print(
            f"Min system lead         : "
            f"{summary['min_time']:.1f}s"
        )

        print(
            f"Max system lead         : "
            f"{summary['max_time']:.1f}s"
        )

        if (
            summary[
                "steady_state_time"
            ]
            is not None
        ):
            print(
                f"Steady state from       : "
                f"{summary['steady_state_time']:.1f}s"
            )

            print(
                f"Steady completed        : "
                f"{summary['steady_state_count']}"
            )

            print(
                f"Steady avg system lead  : "
                f"{summary['steady_state_average_time']:.1f}s"
            )

        print()
        print(
            "TOP 10 LONGEST SYSTEM LEAD TIMES"
        )

        records = list(
            summary[
                "records"
            ]
        )

        records.sort(
            key=lambda item:
                item[
                    "system_lead_time"
                ],
            reverse=True
        )

        for record in records[:10]:
            print(
                f"H={record['hanger_id']} "
                f"request={self._fmt(record['requested_entry'])} "
                f"actual_entry={self._fmt(record['actual_entry'])} "
                f"exit={record['exit_time']:.1f} "
                f"system={record['system_lead_time']:.1f}s "
                f"process={self._fmt(record['process_lead_time'])}s "
                f"entry_wait={self._fmt(record['entry_queue_wait'])}s"
            )

        print(
            "=" * 60
        )