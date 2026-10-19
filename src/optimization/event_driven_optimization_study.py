from dataclasses import dataclass, field
from itertools import islice


@dataclass(frozen=True)
class EventDrivenStudySettings:
    screening_limit: int | None = 500
    finalist_count: int = 10


@dataclass
class EventDrivenStudyResult:
    reference_results: list = field(default_factory=list)
    screening_results: list = field(default_factory=list)
    program_results: list = field(default_factory=list)
    screening_evaluations: int = 0
    program_evaluations: int = 0
    event_rejections: int = 0
    build_or_program_rejections: int = 0
    cancelled: bool = False

    @property
    def evaluated_candidates(self):
        return self.screening_evaluations + self.program_evaluations

    @property
    def cache_hits(self):
        return 0

    @property
    def rejected_candidates(self):
        return self.event_rejections + self.build_or_program_rejections

    @property
    def ranking(self):
        return self.reference_results + self.screening_results

    @property
    def best(self):
        return self.screening_results[0] if self.screening_results else None


class EventDrivenOptimizationStudy:
    """Rank modified EventDriven configurations only.

    PLC generation and ProgramDriven validation are intentionally outside this
    study. The best EventDriven configuration can later be used by the existing
    cyclogram/program workflow.
    """

    def __init__(self, event_evaluator, program_evaluator, settings=None,
                 progress_callback=None, cancel_requested=None,
                 reference_evaluator=None, reference_candidate=None):
        self.event_evaluator = event_evaluator
        self.program_evaluator = program_evaluator
        self.settings = settings or EventDrivenStudySettings()
        self.progress_callback = progress_callback
        self.cancel_requested = cancel_requested or (lambda: False)
        self.reference_evaluator = reference_evaluator
        self.reference_candidate = reference_candidate

    @staticmethod
    def _candidate_key(candidate):
        shared = tuple(
            (item.group_name, item.mode, float(item.value))
            for item in getattr(candidate, "shared_bath_parameters", ())
        )
        return tuple(candidate.start_positions), shared

    @classmethod
    def _sort(cls, results):
        return sorted(
            results,
            key=lambda item: (
                item.status != "VALID",
                item.objective,
                cls._candidate_key(item.candidate)
            )
        )

    def _notify(self, phase, completed, total, result):
        if self.progress_callback is not None:
            self.progress_callback({
                "phase": phase,
                "completed": completed,
                "total": total,
                "result": result,
                "cache_hit": False
            })

    def run(self, candidates):
        limit = self.settings.screening_limit
        if limit is None:
            selected = list(candidates)
        else:
            selected = list(islice(candidates, max(0, int(limit))))
        study = EventDrivenStudyResult()
        if self.reference_evaluator is not None and self.reference_candidate is not None:
            reference = self.reference_evaluator(self.reference_candidate)
            study.reference_results.append(reference)
            self._notify("reference_event", 1, 1, reference)

        for index, candidate in enumerate(selected, start=1):
            if self.cancel_requested():
                study.cancelled = True
                break
            result = self.event_evaluator(candidate)
            metrics = dict(result.metrics)
            metrics["candidate_type"] = "EVENT_CANDIDATE"
            result = type(result)(
                result.candidate, result.status, result.objective,
                metrics, result.rejection_reasons
            )
            study.screening_results.append(result)
            study.screening_evaluations += 1
            study.event_rejections += int(result.status != "VALID")
            self._notify("event_screening", index, len(selected), result)

        study.screening_results = self._sort(study.screening_results)
        if study.cancelled:
            return study
        # EventDriven-only strategy: return all screened rows. No finalist
        # replacement, PLC building or ProgramDriven filtering in this tab.
        return study
