from src.optimization import (
    CandidateResult,
    EventDrivenCandidate,
    EventDrivenOptimizationStudy,
    EventDrivenStudySettings
)


def candidate(value):
    return EventDrivenCandidate((1, 3, 5, 7 + value), ())


class EventEvaluator:
    def __init__(self, calls): self.calls = calls
    def __call__(self, item):
        value = item.start_positions[-1]
        self.calls.append(("event", value))
        valid = value != 10
        return CandidateResult(
            item, "VALID" if valid else "REJECTED",
            (-float(value),),
            {"event_throughput_per_hour": float(value)},
            () if valid else ("EVENT_DEADLOCK",)
        )


class ProgramEvaluator:
    def __init__(self, calls): self.calls = calls
    def __call__(self, event_result):
        value = event_result.candidate.start_positions[-1]
        self.calls.append(("program", value))
        valid = value != 9
        return CandidateResult(
            event_result.candidate,
            "VALID" if valid else "REJECTED",
            (float(value),),
            {"program_cycle_time": float(value)},
            () if valid else ("PROGRAM_EMPTY_PICKUP",)
        )


def test_event_only_study_never_generates_programs():
    calls = []
    study = EventDrivenOptimizationStudy(
        EventEvaluator(calls), ProgramEvaluator(calls),
        EventDrivenStudySettings(screening_limit=4, finalist_count=2)
    ).run([candidate(1), candidate(2), candidate(3), candidate(4)])
    assert study.screening_evaluations == 4
    assert study.program_evaluations == 0
    assert not any(kind == "program" for kind, _ in calls)
    assert len(study.ranking) == 4
    assert study.event_rejections == 1


def test_screening_limit_is_applied_lazily():
    consumed = []
    def candidates():
        for value in range(100):
            consumed.append(value)
            yield candidate(value)
    study = EventDrivenOptimizationStudy(
        EventEvaluator([]), ProgramEvaluator([]),
        EventDrivenStudySettings(screening_limit=3, finalist_count=1)
    ).run(candidates())
    assert consumed == [0, 1, 2]
    assert study.screening_evaluations == 3
    assert study.program_evaluations == 0


def test_progress_reports_distinct_phases():
    events = []
    EventDrivenOptimizationStudy(
        EventEvaluator([]), ProgramEvaluator([]),
        EventDrivenStudySettings(screening_limit=2, finalist_count=1),
        progress_callback=events.append
    ).run([candidate(1), candidate(2)])
    assert [item["phase"] for item in events] == [
        "event_screening", "event_screening"
    ]


def test_cancellation_stops_before_next_candidate():
    state = {"stop": False}
    def progress(_): state["stop"] = True
    study = EventDrivenOptimizationStudy(
        EventEvaluator([]), ProgramEvaluator([]),
        EventDrivenStudySettings(screening_limit=10, finalist_count=2),
        progress_callback=progress,
        cancel_requested=lambda: state["stop"]
    ).run([candidate(1), candidate(2), candidate(3)])
    assert study.cancelled is True
    assert study.screening_evaluations == 1
    assert study.program_evaluations == 0
