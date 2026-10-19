from src.optimization.configuration_clone import (
    clone_configuration_for_candidate
)


class EventDrivenCandidateApplier:
    """Apply scheduling parameters without changing process technology."""

    PROTECTED_STATION_FIELDS = (
        "min_process_time",
        "max_process_time",
        "drip_time",
        "enabled",
        "shared_bath_group"
    )

    def apply(self, base_configuration, candidate):
        configuration = clone_configuration_for_candidate(
            base_configuration
        )
        candidate = candidate.normalized()
        technology_before = {
            int(station.id): tuple(
                getattr(station, field, None)
                for field in self.PROTECTED_STATION_FIELDS
            )
            for station in configuration.stations
        }
        manipulators = {
            int(item.id): item for item in configuration.manipulators
        }
        for manipulator_id, position in enumerate(
            candidate.start_positions, start=1
        ):
            manipulators[manipulator_id].position = int(position)

        by_group = {
            item.group_name: item
            for item in candidate.shared_bath_parameters
        }
        found = set()
        for station in configuration.stations:
            group = str(
                getattr(station, "shared_bath_group", "") or ""
            ).strip()
            parameter = by_group.get(group)
            if parameter is None:
                continue
            station.shared_bath_stagger_mode = parameter.mode
            station.shared_bath_stagger_value = float(parameter.value)
            found.add(group)
        missing = sorted(set(by_group) - found)
        if missing:
            raise ValueError(f"Unknown or inactive shared bath groups: {missing}")

        technology_after = {
            int(station.id): tuple(
                getattr(station, field, None)
                for field in self.PROTECTED_STATION_FIELDS
            )
            for station in configuration.stations
        }
        if technology_after != technology_before:
            raise AssertionError("Candidate changed protected process technology.")
        return configuration
