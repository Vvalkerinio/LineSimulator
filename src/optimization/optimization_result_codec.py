from src.optimization.optimization_candidate import OptimizationCandidate
from src.optimization.optimization_runner import CandidateResult


class OptimizationResultCodec:
    """Serialize ranking data without embedding a heavy SimulationResult."""

    SAFE_METRICS = (
        "event_throughput_per_hour",
        "interval_throughput_per_hour",
        "windowed_steady_throughput_per_hour",
        "throughput_exit_count",
        "throughput_analysis_duration",
        "mean_exit_interval",
        "exit_interval_cv",
        "event_completed_transports",
        "event_processed_events",
        "event_final_time",
        "event_min_residence_failures",
        "event_max_residence_failures",
        "event_deadlock_count",
        "event_watchdog_triggered",
        "shared_bath_retry_limit_reached",
        "steady_state_detected",
        "steady_state_throughput",
        "steady_state_reason",
        "start_positions"
    )

    @classmethod
    def encode(cls, result):
        metrics = {}
        for name in cls.SAFE_METRICS:
            if name not in result.metrics:
                continue
            value = result.metrics[name]
            if isinstance(value, tuple):
                value = list(value)
            metrics[name] = value
        decisions = result.metrics.get("approach_decisions", {})
        metrics["approach_decision_count"] = len(decisions)
        transformation = result.metrics.get("transformation")
        if transformation is not None:
            metrics["inserted_steps"] = int(
                getattr(transformation, "inserted_steps", 0)
            )
            metrics["transformation_notes"] = list(
                getattr(transformation, "notes", [])
            )
        return {
            "status": result.status,
            "objective": list(result.objective),
            "metrics": metrics,
            "rejection_reasons": list(result.rejection_reasons)
        }

    @classmethod
    def decode(cls, candidate, payload):
        metrics = dict(payload.get("metrics", {}))
        for field in ("start_positions", "final_positions"):
            if field in metrics:
                metrics[field] = tuple(metrics[field])
        return CandidateResult(
            candidate=candidate,
            status=payload["status"],
            objective=tuple(payload.get("objective", ())),
            metrics=metrics,
            rejection_reasons=tuple(payload.get("rejection_reasons", ()))
        )
