from src.optimization import CandidateResult, OptimizationCandidate
from src.optimization.trajectory_aware_optimization_pipeline import (
    TrajectoryAwareOptimizationPipeline
)


def candidate():
    return OptimizationCandidate((1, 3, 5, 7), (1, 3, 5, 7))


def test_baseline_material_failure_is_not_blindly_transformed():
    current = candidate()
    baseline = CandidateResult(
        current, "REJECTED", (100,), {"result": object()},
        ("EMPTY_PICKUP", "OCCUPIED_DROP")
    )

    class Evaluator:
        programs = {}
        consults = []
        def __init__(self, answer): self.answer = answer
        def __call__(self, _): return self.answer

    class FailIfUsed:
        def plan(self, *args):
            raise AssertionError("planner must not run for invalid baseline")

    pipeline = TrajectoryAwareOptimizationPipeline(
        Evaluator(baseline), Evaluator(None), FailIfUsed(), object()
    )
    result = pipeline.evaluate(current)
    assert result.rejection_reasons == (
        "BASELINE_EMPTY_PICKUP",
        "BASELINE_OCCUPIED_DROP"
    )
    assert result.metrics["rejection_phase"] == "BASELINE"
