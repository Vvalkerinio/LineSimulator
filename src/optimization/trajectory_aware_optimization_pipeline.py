from copy import deepcopy

from src.optimization.optimization_runner import CandidateResult


class TrajectoryAwareOptimizationPipeline:
    """Two-pass evaluation: baseline timeline, then transformed program."""

    def __init__(self, baseline_evaluator, transformed_evaluator,
                 planner, transformer):
        self.baseline_evaluator = baseline_evaluator
        self.transformed_evaluator = transformed_evaluator
        self.planner = planner
        self.transformer = transformer

    MATERIAL_FLOW_REASONS = {
        "EMPTY_PICKUP",
        "DROP_WITHOUT_HANGER",
        "OCCUPIED_DROP",
        "DEADLOCK"
    }

    @staticmethod
    def _prefix_reasons(result, prefix):
        metrics = dict(result.metrics)
        metrics["rejection_phase"] = prefix
        return CandidateResult(
            candidate=result.candidate,
            status=result.status,
            objective=result.objective,
            metrics=metrics,
            rejection_reasons=tuple(
                f"{prefix}_{reason}" for reason in result.rejection_reasons
            )
        )

    def evaluate(self, candidate):
        baseline = self.baseline_evaluator(candidate)
        baseline_result = baseline.metrics.get("result")
        if baseline_result is None:
            return self._prefix_reasons(baseline, "BASELINE")
        # Parking/preposition cannot repair an already invalid material state.
        # Stop here so the GUI identifies whether the original program+consults
        # are invalid before any optimizer insertion/remap occurs.
        if any(
            reason in self.MATERIAL_FLOW_REASONS
            for reason in baseline.rejection_reasons
        ):
            return self._prefix_reasons(baseline, "BASELINE")
        decisions = self.planner.plan(
            baseline_result,
            self.baseline_evaluator.programs,
            self.baseline_evaluator.consults
        )
        original_transform = self.transformer.transform

        def transform_with_decisions(programs, consults, transformed_candidate):
            return original_transform(
                programs, consults, transformed_candidate,
                approach_positions_by_source=decisions
            )

        class BoundTransformer:
            transform = staticmethod(transform_with_decisions)

        evaluator = deepcopy(self.transformed_evaluator)
        evaluator.transformer = BoundTransformer()
        transformed = evaluator(candidate)
        metrics = dict(transformed.metrics)
        metrics["baseline"] = baseline
        metrics["approach_decisions"] = decisions
        metrics["rejection_phase"] = "TRANSFORMED"
        reasons = transformed.rejection_reasons
        if transformed.status != "VALID":
            reasons = tuple(
                f"TRANSFORMED_{reason}" for reason in reasons
            )
        return CandidateResult(
            candidate=transformed.candidate,
            status=transformed.status,
            objective=transformed.objective,
            metrics=metrics,
            rejection_reasons=reasons
        )
