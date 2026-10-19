from src.optimization.optimization_runner import CandidateResult
from src.optimization.program_candidate_evaluator import ProgramCandidateEvaluator


class ReferenceProgramEvaluator:
    """Run the user's current PLC program and consults without modification."""

    def __init__(self, configuration, programs_provider, consults_provider,
                 cycles=8):
        self.configuration = configuration
        self.programs_provider = programs_provider
        self.consults_provider = consults_provider
        self.cycles = max(2, int(cycles))

    def __call__(self, candidate):
        programs = self.programs_provider()
        if not programs:
            return CandidateResult(
                candidate, "REJECTED", (float("inf"),) * 6,
                {"candidate_type": "REFERENCE_PROGRAM",
                 "evaluation_phase": "REFERENCE_PROGRAM"},
                ("REFERENCE_NO_PROGRAM",)
            )
        result = ProgramCandidateEvaluator(
            self.configuration, programs, self.consults_provider(),
            cycles=self.cycles, initial_state_mode="cycle"
        )(candidate)
        metrics = dict(result.metrics)
        metrics["candidate_type"] = "REFERENCE_PROGRAM"
        metrics["evaluation_phase"] = "REFERENCE_PROGRAM"
        metrics["program_throughput_per_hour"] = metrics.get(
            "throughput_per_hour", 0.0
        )
        return CandidateResult(
            candidate, result.status, result.objective, metrics,
            tuple(f"REFERENCE_{reason}" for reason in result.rejection_reasons)
        )
