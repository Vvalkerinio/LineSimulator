from itertools import product

from src.optimization.optimization_candidate import OptimizationCandidate


class CandidateGenerator:
    """Deterministic grid generator bounded by manipulator work zones."""

    def __init__(self, constraints):
        self.constraints = constraints

    @staticmethod
    def _range_for(manipulator):
        return range(
            int(manipulator.work_zone_start),
            int(manipulator.work_zone_end) + 1
        )

    def generate(self, manipulators, parking_positions_by_manipulator=None):
        manipulators = sorted(manipulators, key=lambda item: int(item.id))
        if len(manipulators) != 4:
            raise ValueError("Optimizer requires exactly M1-M4.")
        start_ranges = [self._range_for(item) for item in manipulators]
        parking_ranges = []
        for item in manipulators:
            allowed = None
            if parking_positions_by_manipulator is not None:
                allowed = parking_positions_by_manipulator.get(int(item.id))
            parking_ranges.append(
                tuple(int(value) for value in allowed)
                if allowed is not None
                else tuple(self._range_for(item))
            )
        for starts in product(*start_ranges):
            if self.constraints.validate_positions(starts, manipulators):
                continue
            for parking in product(*parking_ranges):
                if self.constraints.validate_positions(parking, manipulators):
                    continue
                yield OptimizationCandidate(
                    start_positions=tuple(int(v) for v in starts),
                    parking_positions=tuple(int(v) for v in parking)
                )
