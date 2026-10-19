from dataclasses import dataclass, field
from itertools import islice


@dataclass(frozen=True)
class TheoreticalScreeningSettings:
    screening_limit: int = 5000
    finalist_count: int = 20


@dataclass
class TheoreticalScreeningStudyResult:
    theoretical_results: list = field(default_factory=list)
    finalist_results: list = field(default_factory=list)
    theoretical_evaluations: int = 0
    event_evaluations: int = 0
    cancelled: bool = False

    @property
    def reference_results(self):
        return []

    @property
    def screening_results(self):
        return self.finalist_results

    @property
    def program_results(self):
        return []

    @property
    def screening_evaluations(self):
        return self.theoretical_evaluations

    @property
    def program_evaluations(self):
        return self.event_evaluations

    @property
    def evaluated_candidates(self):
        return self.theoretical_evaluations + self.event_evaluations

    @property
    def cache_hits(self):
        return 0

    @property
    def event_rejections(self):
        return sum(item.status != "VALID" for item in self.finalist_results)

    @property
    def build_or_program_rejections(self):
        return 0

    @property
    def rejected_candidates(self):
        return self.event_rejections + sum(
            item.status == "REJECTED" for item in self.theoretical_results
        )

    @property
    def ranking(self):
        return self.finalist_results + self.theoretical_results

    @property
    def best(self):
        valid = [item for item in self.finalist_results if item.status == "VALID"]
        return valid[0] if valid else None


class TheoreticalScreeningStudy:
    """Analyze every candidate cheaply, then validate diversified finalists."""

    def __init__(self, theoretical_evaluator, event_evaluator, settings=None,
                 progress_callback=None, cancel_requested=None):
        self.theoretical_evaluator = theoretical_evaluator
        self.event_evaluator = event_evaluator
        self.settings = settings or TheoreticalScreeningSettings()
        self.progress_callback = progress_callback
        self.cancel_requested = cancel_requested or (lambda: False)

    @staticmethod
    def _candidate_key(candidate):
        shared = tuple((item.group_name, item.mode, float(item.value))
                       for item in candidate.shared_bath_parameters)
        return tuple(candidate.start_positions), shared

    def _notify(self, phase, completed, total, result):
        if self.progress_callback is not None:
            self.progress_callback({
                "phase": phase,
                "completed": completed,
                "total": total,
                "result": result,
                "cache_hit": False,
            })

    @classmethod
    def _diversified_finalists(cls, ranked, count):
        valid = [item for item in ranked if item.status != "REJECTED"]
        count = min(max(0, int(count)), len(valid))
        if count == 0:
            return []
        global_count = max(1, int(round(count * 0.70)))
        selected = valid[:global_count]
        selected_keys = {cls._candidate_key(item.candidate) for item in selected}

        def add_distinct(key_function, limit):
            seen = {key_function(item.candidate) for item in selected}
            added = 0
            for item in valid:
                candidate_key = cls._candidate_key(item.candidate)
                family = key_function(item.candidate)
                if candidate_key in selected_keys or family in seen:
                    continue
                selected.append(item)
                selected_keys.add(candidate_key)
                seen.add(family)
                added += 1
                if added >= limit or len(selected) >= count:
                    break

        remaining = count - len(selected)
        start_quota = min(remaining, max(1, (count * 15 + 99) // 100))
        add_distinct(lambda candidate: tuple(candidate.start_positions), start_quota)
        remaining = count - len(selected)
        add_distinct(
            lambda candidate: tuple(
                (item.group_name, item.mode, float(item.value))
                for item in candidate.shared_bath_parameters
            ),
            remaining,
        )
        for item in valid:
            key = cls._candidate_key(item.candidate)
            if key not in selected_keys and len(selected) < count:
                selected.append(item)
                selected_keys.add(key)
        return selected[:count]

    def run(self, candidates):
        selected = list(islice(candidates, max(0, int(self.settings.screening_limit))))
        study = TheoreticalScreeningStudyResult()
        for index, candidate in enumerate(selected, start=1):
            if self.cancel_requested():
                study.cancelled = True
                break
            result = self.theoretical_evaluator(candidate)
            study.theoretical_results.append(result)
            study.theoretical_evaluations += 1
            self._notify("theoretical_screening", index, len(selected), result)
        study.theoretical_results.sort(
            key=lambda item: (item.status == "REJECTED", item.objective,
                              self._candidate_key(item.candidate))
        )
        if study.cancelled:
            return study
        finalists = self._diversified_finalists(
            study.theoretical_results, self.settings.finalist_count
        )
        for index, screened in enumerate(finalists, start=1):
            if self.cancel_requested():
                study.cancelled = True
                break
            event_result = self.event_evaluator(screened.candidate)
            metrics = dict(event_result.metrics)
            metrics.update(screened.metrics)
            metrics.update({
                "candidate_type": "EVENT_CANDIDATE",
                "screened_by": "THEORETICAL",
                "theoretical_rank": study.theoretical_results.index(screened) + 1,
            })
            event_result = type(event_result)(
                event_result.candidate,
                event_result.status,
                event_result.objective,
                metrics,
                event_result.rejection_reasons,
            )
            study.finalist_results.append(event_result)
            study.event_evaluations += 1
            self._notify("event_finalists", index, len(finalists), event_result)
        study.finalist_results.sort(
            key=lambda item: (item.status != "VALID", item.objective,
                              self._candidate_key(item.candidate))
        )
        return study
