from collections import defaultdict
from itertools import product

from src.optimization.event_driven_candidate import EventDrivenCandidate
from src.optimization.optimization_constraints import OptimizationConstraints


class EventDrivenCandidateGenerator:
    """Generate legal candidates from the closest reference neighbourhood out."""

    def __init__(self, constraints, shared_bath_generator):
        self.constraints = constraints
        self.shared_bath_generator = shared_bath_generator

    @staticmethod
    def _current_shared_parameters(configuration):
        from src.optimization.event_driven_candidate import (
            SharedBathCandidateParameter
        )
        groups = {}
        for station in configuration.stations:
            name = str(getattr(station, "shared_bath_group", "") or "").strip()
            if not name or not bool(getattr(station, "enabled", True)):
                continue
            groups.setdefault(name, []).append(station)
        parameters = []
        for name, stations in sorted(groups.items()):
            if len(stations) < 2:
                continue
            station = stations[0]
            parameters.append(SharedBathCandidateParameter(
                name,
                getattr(station, "shared_bath_stagger_mode", "percent"),
                getattr(station, "shared_bath_stagger_value", 50.0)
            ).normalized())
        return tuple(parameters)

    @staticmethod
    def _start_ranges(manipulators):
        return [
            range(int(item.work_zone_start), int(item.work_zone_end) + 1)
            for item in manipulators
        ]

    @staticmethod
    def _start_distance(values, reference):
        deltas = tuple(abs(int(value) - int(base))
                       for value, base in zip(values, reference))
        return sum(deltas), max(deltas), sum(delta > 0 for delta in deltas)

    @staticmethod
    def _parameter_distance(parameter, reference):
        if reference is None:
            return 8.0
        mode = str(parameter.mode).lower()
        reference_mode = str(reference.mode).lower()
        value = float(parameter.value)
        reference_value = float(reference.value)
        if mode == reference_mode:
            step = 10.0 if mode == "percent" else 15.0 if mode == "seconds" else 1.0
            return abs(value - reference_value) / step
        # A mode change is deliberately later than the nearest numeric changes.
        # Alternate has no numeric magnitude; other modes receive a small
        # normalized distance from their neutral/default point as a tie-break.
        mode_penalty = 4.0
        if mode == "percent":
            return mode_penalty + abs(value - 50.0) / 10.0
        if mode == "seconds":
            return mode_penalty + abs(value) / 15.0
        return mode_penalty

    @classmethod
    def _shared_distance(cls, parameters, current_parameters):
        current = {item.group_name: item for item in current_parameters}
        value = sum(
            cls._parameter_distance(item, current.get(item.group_name))
            for item in parameters
        )
        return round(value, 6)

    def _legal_start_groups(self, manipulators):
        reference = tuple(int(item.position) for item in manipulators)
        groups = defaultdict(list)
        for values in product(*self._start_ranges(manipulators)):
            values = tuple(int(value) for value in values)
            if self.constraints.validate_positions(values, manipulators):
                continue
            distance, maximum, changed = self._start_distance(values, reference)
            groups[float(distance)].append((maximum, changed, values))
        for distance in groups:
            groups[distance].sort(key=lambda item: (item[0], item[1], item[2]))
        return reference, groups

    def generate(self, configuration):
        manipulators = sorted(
            configuration.manipulators,
            key=lambda item: int(item.id)
        )
        if len(manipulators) != 4:
            raise ValueError("EventDriven optimizer requires exactly M1-M4.")

        current_parameters = self._current_shared_parameters(configuration)
        generated = tuple(self.shared_bath_generator.generate(configuration))
        shared_variants = (current_parameters,) + tuple(
            tuple(item) for item in generated if tuple(item) != current_parameters
        )
        shared_groups = defaultdict(list)
        for parameters in shared_variants:
            score = self._shared_distance(parameters, current_parameters)
            shared_groups[score].append(tuple(parameters))
        for score in shared_groups:
            shared_groups[score].sort(key=lambda parameters: tuple(
                (item.group_name, item.mode, float(item.value))
                for item in parameters
            ))

        _, start_groups = self._legal_start_groups(manipulators)
        total_scores = sorted({
            start_score + shared_score
            for start_score in start_groups
            for shared_score in shared_groups
        })
        seen = set()
        for total_score in total_scores:
            for start_score in sorted(start_groups):
                shared_score = round(total_score - start_score, 6)
                if shared_score not in shared_groups:
                    continue
                for _, _, starts in start_groups[start_score]:
                    for parameters in shared_groups[shared_score]:
                        candidate = EventDrivenCandidate(
                            start_positions=starts,
                            shared_bath_parameters=parameters
                        ).normalized()
                        key = (
                            candidate.start_positions,
                            candidate.shared_bath_parameters
                        )
                        if key in seen:
                            continue
                        seen.add(key)
                        yield candidate
