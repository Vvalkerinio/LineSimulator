from dataclasses import dataclass


@dataclass(frozen=True)
class OptimizationCandidate:
    """One reproducible set of start and parking positions for M1-M4."""

    start_positions: tuple[int, int, int, int]
    parking_positions: tuple[int, int, int, int]

    def position_for(self, manipulator_id: int, parking: bool = False) -> int:
        if manipulator_id not in (1, 2, 3, 4):
            raise ValueError(f"Unsupported manipulator id: {manipulator_id}")
        source = self.parking_positions if parking else self.start_positions
        return int(source[manipulator_id - 1])
