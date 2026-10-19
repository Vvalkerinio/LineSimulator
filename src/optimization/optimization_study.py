from dataclasses import dataclass, field
from itertools import islice

from src.optimization.optimization_result_codec import OptimizationResultCodec


@dataclass(frozen=True)
class OptimizationStudySettings:
    screening_limit: int | None = None
    finalist_count: int = 10
    screening_cycles: int = 2
    final_cycles: int = 8


@dataclass
class OptimizationStudyResult:
    screening_results: list = field(default_factory=list)
    finalist_results: list = field(default_factory=list)
    evaluated_candidates: int = 0
    cache_hits: int = 0
    rejected_candidates: int = 0
    cancelled: bool = False

    @property
    def ranking(self):
        return self.finalist_results or self.screening_results

    @property
    def best(self):
        ranking = self.ranking
        return ranking[0] if ranking else None


class OptimizationStudy:
    """Two-phase batch study with cache, resume and early rejection."""

    def __init__(self, screening_evaluator, final_evaluator, settings,
                 cache=None, progress_callback=None, cancel_requested=None):
        self.screening_evaluator = screening_evaluator
        self.final_evaluator = final_evaluator
        self.settings = settings
        self.cache = cache
        self.progress_callback = progress_callback
        self.cancel_requested = cancel_requested or (lambda: False)

    @staticmethod
    def _sort(results):
        return sorted(
            results,
            key=lambda item: (
                item.status != "VALID",
                item.objective,
                item.candidate.start_positions,
                item.candidate.parking_positions
            )
        )

    def _notify(self, phase, completed, total, result, cache_hit):
        if self.progress_callback is not None:
            self.progress_callback({
                "phase": phase,
                "completed": completed,
                "total": total,
                "result": result,
                "cache_hit": cache_hit
            })

    def _evaluate(self, candidate, phase, evaluator):
        if self.cache is not None:
            cached = self.cache.get(candidate, phase)
            if cached is not None:
                return (
                    OptimizationResultCodec.decode(
                        candidate, cached["result"]
                    ),
                    True
                )
        result = evaluator(candidate)
        if self.cache is not None:
            self.cache.put(
                candidate, phase, OptimizationResultCodec.encode(result)
            )
        return result, False

    def run(self, candidates):
        if self.settings.screening_limit is not None:
            candidates = list(islice(
                candidates,
                max(0, int(self.settings.screening_limit))
            ))
        else:
            candidates = list(candidates)
        study = OptimizationStudyResult()
        total = len(candidates)

        for index, candidate in enumerate(candidates, start=1):
            if self.cancel_requested():
                study.cancelled = True
                break
            result, cache_hit = self._evaluate(
                candidate, "screening", self.screening_evaluator
            )
            study.screening_results.append(result)
            study.evaluated_candidates += 1
            study.cache_hits += int(cache_hit)
            study.rejected_candidates += int(result.status != "VALID")
            self._notify("screening", index, total, result, cache_hit)

        study.screening_results = self._sort(study.screening_results)
        if study.cancelled:
            return study

        valid = [
            item for item in study.screening_results
            if item.status == "VALID"
        ][:max(0, int(self.settings.finalist_count))]

        for index, screened in enumerate(valid, start=1):
            if self.cancel_requested():
                study.cancelled = True
                break
            result, cache_hit = self._evaluate(
                screened.candidate, "final", self.final_evaluator
            )
            result.metrics.setdefault("screening", screened)
            study.finalist_results.append(result)
            study.evaluated_candidates += 1
            study.cache_hits += int(cache_hit)
            study.rejected_candidates += int(result.status != "VALID")
            self._notify("final", index, len(valid), result, cache_hit)

        study.finalist_results = self._sort(study.finalist_results)
        return study
