from dataclasses import dataclass


@dataclass(frozen=True)
class ConstraintViolation:
    code: str
    message: str
    manipulator_ids: tuple[int, ...] = ()


class OptimizationConstraints:
    """Hard positional constraints for all optimization candidates."""

    def __init__(self, minimum_position_difference=2.0):
        self.minimum_position_difference = max(
            0.0,
            float(minimum_position_difference)
        )

    def validate_positions(self, positions, manipulators=None):
        if len(positions) != 4:
            return [ConstraintViolation(
                "POSITION_COUNT",
                "Exactly four manipulator positions are required."
            )]
        values = tuple(float(value) for value in positions)
        violations = []
        for index in range(3):
            left_id, right_id = index + 1, index + 2
            left, right = values[index], values[index + 1]
            if left >= right:
                violations.append(ConstraintViolation(
                    "MANIPULATOR_ORDER",
                    f"M{left_id}={left:g} must be before M{right_id}={right:g}.",
                    (left_id, right_id)
                ))
            elif right - left < self.minimum_position_difference:
                violations.append(ConstraintViolation(
                    "MINIMUM_SPACING",
                    f"M{left_id}={left:g}, M{right_id}={right:g}: required "
                    f"difference is {self.minimum_position_difference:g}.",
                    (left_id, right_id)
                ))
        if manipulators is not None:
            by_id = {int(item.id): item for item in manipulators}
            for manipulator_id, position in enumerate(values, start=1):
                manipulator = by_id.get(manipulator_id)
                if manipulator is None:
                    violations.append(ConstraintViolation(
                        "MISSING_MANIPULATOR",
                        f"M{manipulator_id} is missing.",
                        (manipulator_id,)
                    ))
                    continue
                minimum = float(getattr(manipulator, "work_zone_start", position))
                maximum = float(getattr(manipulator, "work_zone_end", position))
                if not minimum <= position <= maximum:
                    violations.append(ConstraintViolation(
                        "OUTSIDE_WORK_ZONE",
                        f"M{manipulator_id} position {position:g} outside "
                        f"{minimum:g}..{maximum:g}.",
                        (manipulator_id,)
                    ))
        return violations

    def is_legal_position(self, manipulator_id, candidate_position, positions):
        updated = list(positions)
        updated[int(manipulator_id) - 1] = candidate_position
        return not self.validate_positions(updated)
