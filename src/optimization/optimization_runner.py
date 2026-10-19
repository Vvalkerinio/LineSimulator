from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateResult:
    candidate: object
    status: str
    objective: tuple
    metrics: dict
    rejection_reasons: tuple[str, ...] = ()


class OptimizationRunner:
    """Runs candidates through an injected full-simulation evaluator."""

    def __init__(self, evaluator):
        self.evaluator = evaluator

    def run(self, candidates, limit=None):
        results = []
        for index, candidate in enumerate(candidates):
            if limit is not None and index >= int(limit):
                break
            results.append(self.evaluator(candidate))
        return sorted(
            results,
            key=lambda result: (
                result.status != "VALID",
                result.objective,
                result.candidate.start_positions,
                result.candidate.parking_positions
            )
        )
