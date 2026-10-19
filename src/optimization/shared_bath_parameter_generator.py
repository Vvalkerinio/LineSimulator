from itertools import product

from src.optimization.event_driven_candidate import (
    SharedBathCandidateParameter
)


class SharedBathParameterGenerator:
    """Generate only modes and values implemented by SharedBathSelector."""

    SUPPORTED_MODES = ("percent", "seconds", "alternate")

    def __init__(self, percent_values=None, seconds_values=None,
                 modes=None):
        self.percent_values = tuple(
            float(value) for value in (
                percent_values if percent_values is not None
                else (20, 30, 40, 50, 60, 70, 80)
            )
        )
        self.seconds_values = tuple(
            float(value) for value in (
                seconds_values if seconds_values is not None
                else (0, 15, 30, 45, 60)
            )
        )
        self.modes = tuple(modes or self.SUPPORTED_MODES)
        unknown = set(self.modes) - set(self.SUPPORTED_MODES)
        if unknown:
            raise ValueError(f"Unsupported shared bath modes: {sorted(unknown)}")

    @staticmethod
    def active_groups(configuration):
        groups = {}
        for station in getattr(configuration, "stations", []):
            if not bool(getattr(station, "enabled", True)):
                continue
            name = str(getattr(station, "shared_bath_group", "") or "").strip()
            if not name:
                continue
            groups.setdefault(name, []).append(int(station.id))
        return {
            name: tuple(sorted(ids))
            for name, ids in sorted(groups.items())
            if len(ids) >= 2
        }

    def variants_for_group(self, group_name):
        variants = []
        for mode in self.modes:
            if mode == "percent":
                variants.extend(
                    SharedBathCandidateParameter(group_name, mode, value)
                    for value in self.percent_values
                    if 0.0 <= value <= 100.0
                )
            elif mode == "seconds":
                variants.extend(
                    SharedBathCandidateParameter(group_name, mode, value)
                    for value in self.seconds_values
                    if value >= 0.0
                )
            else:
                variants.append(
                    SharedBathCandidateParameter(group_name, "alternate", 0.0)
                )
        return tuple(item.normalized() for item in variants)

    def generate(self, configuration):
        groups = self.active_groups(configuration)
        if not groups:
            yield ()
            return
        names = tuple(groups)
        choices = [self.variants_for_group(name) for name in names]
        yield from product(*choices)
