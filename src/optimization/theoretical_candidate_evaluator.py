from math import inf

from src.analysis.theoretical_capacity_analyzer import TheoreticalCapacityAnalyzer
from src.optimization.event_driven_candidate_applier import EventDrivenCandidateApplier
from src.optimization.optimization_runner import CandidateResult


class TheoreticalCandidateEvaluator:
    """Fast candidate-specific proxy used only before EventDriven validation."""

    SCREENED = "THEORETICAL"
    REJECTED = "REJECTED"

    def __init__(self, configuration, analyzer=None, candidate_applier=None):
        self.base_configuration = configuration
        self.analyzer = analyzer or TheoreticalCapacityAnalyzer()
        self.candidate_applier = candidate_applier or EventDrivenCandidateApplier()

    @staticmethod
    def _route(configuration):
        route, groups = [], set()
        for station in configuration.stations:
            if not bool(getattr(station, "enabled", True)):
                continue
            group = str(getattr(station, "shared_bath_group", "") or "").strip()
            if group and group.lower() != "none":
                if group in groups:
                    continue
                groups.add(group)
            route.append(int(station.id))
        return tuple(route)

    @staticmethod
    def _spacing(configuration, starts):
        required = float(getattr(configuration, "minimum_manipulator_spacing", 0.0))
        margins = [float(right) - float(left) - required
                   for left, right in zip(starts, starts[1:])]
        return min(margins) if margins else inf

    @staticmethod
    def _startup_access(configuration, route):
        total = 0.0
        details = []
        for manipulator in configuration.manipulators:
            sources = []
            for source, target in zip(route, route[1:]):
                if manipulator.is_transport_inside_work_zone(source, target):
                    sources.append(source)
            if not sources:
                continue
            distance = min(abs(int(manipulator.position) - int(source)) for source in sources)
            seconds = distance * float(manipulator.travel_time_per_position)
            total += seconds
            details.append({
                "manipulator_id": int(manipulator.id),
                "minimum_empty_distance": distance,
                "minimum_empty_seconds": seconds,
            })
        return total, details

    @staticmethod
    def _zone_center_penalty(configuration):
        penalty = 0.0
        for manipulator in configuration.manipulators:
            center = (
                float(manipulator.work_zone_start)
                + float(manipulator.work_zone_end)
            ) / 2.0
            penalty += abs(float(manipulator.position) - center)
        return penalty

    @staticmethod
    def _shared_bath_penalty(configuration, candidate):
        groups = {}
        for station in configuration.stations:
            group = str(getattr(station, "shared_bath_group", "") or "").strip()
            if group:
                groups.setdefault(group, []).append(station)
        penalty = 0.0
        details = []
        for parameter in candidate.shared_bath_parameters:
            mode = str(parameter.mode).lower()
            if mode == "alternate":
                item_penalty = 0.0
            elif mode == "percent":
                item_penalty = abs(float(parameter.value) - 50.0) / 50.0
            else:
                minimums = [float(item.min_process_time)
                            for item in groups.get(parameter.group_name, ())]
                reference = min(minimums) if minimums else 1.0
                item_penalty = abs(float(parameter.value) - reference / 2.0) / max(reference, 1.0)
            penalty += item_penalty
            details.append({
                "group": parameter.group_name,
                "mode": mode,
                "value": float(parameter.value),
                "penalty": item_penalty,
            })
        return penalty, details

    def __call__(self, candidate):
        configuration = self.candidate_applier.apply(self.base_configuration, candidate)
        starts = tuple(int(item.position) for item in configuration.manipulators)
        route = self._route(configuration)
        spacing_margin = self._spacing(configuration, starts)
        report = self.analyzer.analyze(configuration, route=route)
        startup_seconds, startup_details = self._startup_access(configuration, route)
        center_penalty = self._zone_center_penalty(configuration)
        shared_penalty, shared_details = self._shared_bath_penalty(configuration, candidate)

        reasons = []
        unreachable = int(report.nominal_upper_bound <= 0.0)
        if unreachable:
            reasons.append("THEORETICAL_UNREACHABLE_TRANSITION")
        if spacing_margin < 0.0:
            reasons.append("THEORETICAL_START_SPACING")

        metrics = {
            "candidate_type": "THEORETICAL_CANDIDATE",
            "evaluation_phase": "THEORETICAL_SCREENING",
            "theoretical_nominal_upper_bound": float(report.nominal_upper_bound),
            "theoretical_possible_upper_bound": float(report.possible_upper_bound),
            "theoretical_limiting_resource": report.nominal_limiting_resource,
            "theoretical_possible_limiting_resource": report.possible_limiting_resource,
            "theoretical_startup_access_seconds": startup_seconds,
            "theoretical_zone_center_penalty": center_penalty,
            "theoretical_shared_bath_penalty": shared_penalty,
            "theoretical_start_spacing_margin": spacing_margin,
            "theoretical_startup_details": startup_details,
            "theoretical_shared_bath_details": shared_details,
        }
        objective = (
            unreachable,
            -float(report.possible_upper_bound),
            -float(report.nominal_upper_bound),
            startup_seconds,
            shared_penalty,
            center_penalty,
            -spacing_margin,
        )
        return CandidateResult(
            candidate=candidate,
            status=self.REJECTED if reasons else self.SCREENED,
            objective=objective,
            metrics=metrics,
            rejection_reasons=tuple(reasons),
        )
