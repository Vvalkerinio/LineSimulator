class SimulationPreflightError(ValueError):
    """Raised before a run when the configured physical start is impossible."""


class SimulationPreflightValidator:
    MIN_STATION_ID = 1
    MAX_STATION_ID = 22
    EPSILON = 1e-9

    def validate(self, configuration, initial_positions=None):
        errors = []
        manipulators = sorted(
            tuple(getattr(configuration, "manipulators", ()) or ()),
            key=lambda item: int(item.id)
        )
        stations = tuple(getattr(configuration, "stations", ()) or ())
        self._validate_station_ids(stations, errors)
        self._validate_process_limits(stations, errors)
        self._validate_manipulators(
            manipulators,
            float(getattr(configuration, "minimum_manipulator_spacing", 0.0)),
            initial_positions or {},
            errors
        )
        if errors:
            raise SimulationPreflightError(
                "Nieprawidłowy stan początkowy symulacji:\n- "
                + "\n- ".join(errors)
            )
        return True

    def _validate_station_ids(self, stations, errors):
        ids = [int(station.id) for station in stations]
        if len(ids) != len(set(ids)):
            errors.append("identyfikatory stanowisk nie są unikalne")
        outside = [
            value for value in ids
            if not self.MIN_STATION_ID <= value <= self.MAX_STATION_ID
        ]
        if outside:
            errors.append(f"stanowiska poza geometrią 1..22: {outside}")

    @staticmethod
    def _limit(station, name, fallback):
        value = getattr(station, name, fallback)
        return float(fallback if value is None else value)

    def _validate_process_limits(self, stations, errors):
        for station in stations:
            if not bool(getattr(station, "is_process_bath", True)):
                continue
            nominal_min = self._limit(station, "min_process_time", 0.0)
            nominal_max = self._limit(station, "max_process_time", nominal_min)
            possible_min = self._limit(
                station, "possible_min_process_time", nominal_min
            )
            possible_max = self._limit(
                station, "possible_max_process_time", nominal_max
            )
            if not (
                possible_min <= nominal_min <= nominal_max <= possible_max
            ):
                errors.append(
                    f"S{station.id}: wymagane Possible Min <= Min <= Max "
                    f"<= Possible Max, otrzymano {possible_min}, "
                    f"{nominal_min}, {nominal_max}, {possible_max}"
                )

    def _validate_manipulators(
        self, manipulators, required_spacing, initial_positions, errors
    ):
        ids = [int(item.id) for item in manipulators]
        if len(ids) != len(set(ids)):
            errors.append("identyfikatory manipulatorów nie są unikalne")
            return
        resolved = []
        for manipulator in manipulators:
            manipulator_id = int(manipulator.id)
            position = int(initial_positions.get(
                manipulator_id, manipulator.position
            ))
            zone_start = int(getattr(manipulator, "work_zone_start", 1))
            zone_end = int(getattr(manipulator, "work_zone_end", 22))
            if zone_start > zone_end:
                errors.append(
                    f"M{manipulator_id}: początek strefy {zone_start} "
                    f"jest większy od końca {zone_end}"
                )
            if not zone_start <= position <= zone_end:
                errors.append(
                    f"M{manipulator_id}: pozycja startowa {position} "
                    f"nie należy do strefy {zone_start}..{zone_end}"
                )
            parking = int(getattr(
                manipulator, "preferred_parking_position", position
            ))
            if not zone_start <= parking <= zone_end:
                errors.append(
                    f"M{manipulator_id}: parking {parking} "
                    f"nie należy do strefy {zone_start}..{zone_end}"
                )
            resolved.append((manipulator_id, position))
        for (left_id, left), (right_id, right) in zip(resolved, resolved[1:]):
            if right < left:
                errors.append(
                    f"kolejność M{left_id}/M{right_id} narusza brak mijania: "
                    f"{left} > {right}"
                )
            distance = right - left
            if distance + self.EPSILON < required_spacing:
                errors.append(
                    f"M{left_id}/M{right_id}: odstęp startowy {distance:.1f} "
                    f"jest mniejszy od wymaganego {required_spacing:.1f}"
                )
