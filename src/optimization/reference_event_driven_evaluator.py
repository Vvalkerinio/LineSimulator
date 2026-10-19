from copy import deepcopy

from src.optimization.event_driven_candidate_evaluator import (
    EventDrivenCandidateEvaluator
)


class _IdentityCandidateApplier:
    """Preserve the exact GUI configuration for the control run."""

    @staticmethod
    def apply(configuration, candidate):
        return deepcopy(configuration)


class ReferenceEventDrivenEvaluator:
    """Run current EventDriven settings without applying candidate changes."""

    def __init__(self, configuration, simulator_factory=None):
        self.evaluator = EventDrivenCandidateEvaluator(
            configuration,
            simulator_factory=simulator_factory,
            candidate_applier=_IdentityCandidateApplier()
        )

    def __call__(self, candidate):
        result = self.evaluator(candidate)
        result.metrics["candidate_type"] = "REFERENCE_EVENT"
        result.metrics["evaluation_phase"] = "REFERENCE_EVENT"
        result.metrics["reference_exact_configuration"] = True
        return result
