import csv
import json
from pathlib import Path

from src.optimization.optimization_result_codec import OptimizationResultCodec


class OptimizationReport:
    """Export EventDriven-only optimization ranking."""

    CSV_FIELDS = (
        "rank", "candidate_type", "evaluation_phase", "status",
        "start_positions", "shared_bath",
        "theoretical_rank", "theoretical_nominal_upper_bound",
        "theoretical_possible_upper_bound", "theoretical_limiting_resource",
        "theoretical_startup_access_seconds",
        "theoretical_shared_bath_penalty", "theoretical_start_spacing_margin",
        "event_throughput_per_hour", "event_completed_transports",
        "event_processed_events", "event_final_time",
        "event_min_residence_failures", "event_max_residence_failures",
        "event_deadlock_count", "rejection_reasons"
    )

    @staticmethod
    def _shared_bath(candidate):
        return ";".join(
            f"{item.group_name}:{item.mode}={item.value:g}"
            for item in getattr(candidate, "shared_bath_parameters", ())
        )

    @classmethod
    def _row(cls, rank, result):
        metrics = result.metrics
        return {
            "rank": rank,
            "candidate_type": metrics.get("candidate_type", "EVENT_CANDIDATE"),
            "evaluation_phase": metrics.get("evaluation_phase", "EVENT_DRIVEN"),
            "status": result.status,
            "start_positions": "-".join(map(
                str, result.candidate.start_positions
            )),
            "shared_bath": cls._shared_bath(result.candidate),
            "theoretical_rank": metrics.get("theoretical_rank", ""),
            "theoretical_nominal_upper_bound": metrics.get(
                "theoretical_nominal_upper_bound", ""
            ),
            "theoretical_possible_upper_bound": metrics.get(
                "theoretical_possible_upper_bound", ""
            ),
            "theoretical_limiting_resource": metrics.get(
                "theoretical_limiting_resource", ""
            ),
            "theoretical_startup_access_seconds": metrics.get(
                "theoretical_startup_access_seconds", ""
            ),
            "theoretical_shared_bath_penalty": metrics.get(
                "theoretical_shared_bath_penalty", ""
            ),
            "theoretical_start_spacing_margin": metrics.get(
                "theoretical_start_spacing_margin", ""
            ),
            "event_throughput_per_hour": metrics.get(
                "event_throughput_per_hour", ""
            ),
            "event_completed_transports": metrics.get(
                "event_completed_transports", ""
            ),
            "event_processed_events": metrics.get(
                "event_processed_events", ""
            ),
            "event_final_time": metrics.get("event_final_time", ""),
            "event_min_residence_failures": metrics.get(
                "event_min_residence_failures", ""
            ),
            "event_max_residence_failures": metrics.get(
                "event_max_residence_failures", ""
            ),
            "event_deadlock_count": metrics.get(
                "event_deadlock_count", ""
            ),
            "rejection_reasons": ";".join(result.rejection_reasons)
        }

    def write_csv(self, path, study_result):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.CSV_FIELDS)
            writer.writeheader()
            for rank, result in enumerate(study_result.ranking, start=1):
                writer.writerow(self._row(rank, result))
        return path

    def write_json(self, path, study_result):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "evaluated_candidates": study_result.evaluated_candidates,
            "rejected_candidates": study_result.rejected_candidates,
            "cancelled": study_result.cancelled,
            "ranking": [
                {
                    "candidate": {
                        "start_positions": list(item.candidate.start_positions),
                        "shared_bath_parameters": [
                            {
                                "group_name": parameter.group_name,
                                "mode": parameter.mode,
                                "value": parameter.value
                            }
                            for parameter in getattr(
                                item.candidate, "shared_bath_parameters", ()
                            )
                        ]
                    },
                    "result": OptimizationResultCodec.encode(item)
                }
                for item in study_result.ranking
            ]
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8"
        )
        return path
