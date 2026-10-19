from dataclasses import dataclass


@dataclass(frozen=True)
class CycleClosureViolation:
    code: str
    message: str


class CycleClosureValidator:
    """Validate that a PLC cycle returns to the same repeatable state."""

    def validate(self, start_positions, end_positions,
                 carrying_at_end=None, active_consults=None,
                 transfer_state_start=None, transfer_state_end=None):
        violations = []
        if tuple(start_positions) != tuple(end_positions):
            violations.append(CycleClosureViolation(
                "CYCLE_POSITION_NOT_CLOSED",
                f"start={tuple(start_positions)}, end={tuple(end_positions)}"
            ))
        carrying_at_end = carrying_at_end or {}
        loaded = [mid for mid, hanger in carrying_at_end.items()
                  if hanger is not None]
        if loaded:
            violations.append(CycleClosureViolation(
                "CYCLE_HANGER_ON_MANIPULATOR",
                f"Manipulators carrying hangers at cycle end: {loaded}"
            ))
        if active_consults:
            violations.append(CycleClosureViolation(
                "CYCLE_ACTIVE_CONSULT",
                f"Active consults cross cycle boundary: {len(active_consults)}"
            ))
        if transfer_state_start is not None and transfer_state_end is not None:
            if transfer_state_start != transfer_state_end:
                violations.append(CycleClosureViolation(
                    "CYCLE_TRANSFER_STATE_NOT_CLOSED",
                    "ST23/ST24 state differs at cycle boundary."
                ))
        return violations
