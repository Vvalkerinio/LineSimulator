from collections import defaultdict

from src.model.shared_bath_group import (
    SharedBathGroup
)


class SharedBathGroupBuilder:

    def build(
        self,
        stations
    ):

        groups = defaultdict(
            list
        )

        for station in stations:

            group = getattr(
                station,
                "shared_bath_group",
                None
            )

            if group is None:

                continue

            group = (
                str(group)
                .strip()
            )

            if (
                group == ""
                or group.lower() == "none"
            ):

                continue

            groups[
                group
            ].append(
                station.id
            )

        result = []

        for group_id in sorted(
            groups.keys()
        ):

            station_ids = sorted(
                groups[
                    group_id
                ]
            )

            if len(
                station_ids
            ) < 2:

                continue

            result.append(
                SharedBathGroup(
                    group_id=
                        group_id,
                    station_ids=
                        station_ids
                )
            )

        return result