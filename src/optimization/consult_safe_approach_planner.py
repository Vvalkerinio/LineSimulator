from dataclasses import dataclass


@dataclass(frozen=True)
class ApproachPlan:
    action: str
    from_position: int
    approach_position: int
    final_target: int
    travel_time: float
    predicted_release_time: float
    gross_consult_wait: float
    productive_approach_time: float
    net_idle_wait: float
    forced_process_bath: bool


class ConsultSafeApproachPlanner:
    """Use consult waiting time for a safe empty approach toward the target."""

    def __init__(self, parking_selector):
        self.parking_selector = parking_selector

    def plan(self, manipulator_id, current_positions, target_position,
             current_time, predicted_release_time, travel_time_per_position,
             stations, zone_start, zone_end, path_is_safe=None):
        decision = self.parking_selector.select(
            manipulator_id=manipulator_id,
            current_positions=current_positions,
            target_position=target_position,
            stations=stations,
            zone_start=zone_start,
            zone_end=zone_end,
            path_is_safe=path_is_safe
        )
        current = int(current_positions[int(manipulator_id) - 1])
        travel_time = abs(decision.position - current) * float(
            travel_time_per_position
        )
        gross = max(0.0, float(predicted_release_time) - float(current_time))
        productive = min(gross, travel_time)
        net_idle = max(0.0, gross - productive)
        action = "WAIT_IN_PLACE" if decision.position == current else "APPROACH_PARTIAL"
        return ApproachPlan(
            action=action,
            from_position=current,
            approach_position=decision.position,
            final_target=int(target_position),
            travel_time=travel_time,
            predicted_release_time=float(predicted_release_time),
            gross_consult_wait=gross,
            productive_approach_time=productive,
            net_idle_wait=net_idle,
            forced_process_bath=decision.forced_process_bath
        )
