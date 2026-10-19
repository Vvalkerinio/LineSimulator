from types import SimpleNamespace

from src.optimization import (
    CandidateResult, EventDrivenCandidate, EventDrivenCandidateEvaluator,
    EventDrivenCandidateGenerator, EventDrivenOptimizationStudy,
    EventDrivenStudySettings, OptimizationConstraints,
    ReferenceProgramEvaluator, SharedBathParameterGenerator
)


def config():
    stations = [
        SimpleNamespace(id=1, enabled=True, shared_bath_group="ODT",
                        shared_bath_stagger_mode="seconds",
                        shared_bath_stagger_value=37.0),
        SimpleNamespace(id=2, enabled=True, shared_bath_group="ODT",
                        shared_bath_stagger_mode="seconds",
                        shared_bath_stagger_value=37.0)
    ]
    manipulators = [
        SimpleNamespace(id=i, position=2*i, work_zone_start=2*i,
                        work_zone_end=2*i+1) for i in range(1, 5)
    ]
    return SimpleNamespace(stations=stations, manipulators=manipulators,
                           minimum_manipulator_spacing=2)


def test_current_start_and_exact_shared_bath_are_first():
    generator = EventDrivenCandidateGenerator(
        OptimizationConstraints(2), SharedBathParameterGenerator()
    )
    first = next(generator.generate(config()))
    assert first.start_positions == (2, 4, 6, 8)
    assert [(p.group_name, p.mode, p.value)
            for p in first.shared_bath_parameters] == [
                ("ODT", "seconds", 37.0)
            ]


def test_positive_steady_throughput_does_not_claim_no_transport():
    evaluator = EventDrivenCandidateEvaluator.__new__(EventDrivenCandidateEvaluator)
    result = SimpleNamespace(
        deadlocks=[], process_violations=[], process_compliance=[],
        processed_events=10, completed_transports=0,
        steady_state={"detected": True, "throughput": 12.0}
    )
    kpi = SimpleNamespace(transports_per_hour=0.0)
    reasons = evaluator._rejection_reasons(
        result, kpi, evaluator._steady_state_metrics(result)
    )
    assert "EVENT_NO_COMPLETED_TRANSPORT" not in reasons
    assert "EVENT_ZERO_THROUGHPUT" not in reasons


def test_reference_is_visible_in_event_only_mode():
    candidate = EventDrivenCandidate((1, 3, 5, 7), ())
    reference = CandidateResult(candidate, "VALID", (0,),
                                {"candidate_type": "REFERENCE_PROGRAM"}, ())
    screened = CandidateResult(candidate, "VALID", (1,), {}, ())
    study = EventDrivenOptimizationStudy(
        lambda _: screened, None,
        EventDrivenStudySettings(1, 1),
        reference_evaluator=lambda _: reference,
        reference_candidate=candidate
    ).run([candidate])
    assert len(study.ranking) == 2
    assert study.ranking[0].metrics["candidate_type"] == "REFERENCE_PROGRAM"
    assert study.ranking[1].metrics["candidate_type"] == "EVENT_CANDIDATE"
    assert study.best is study.screening_results[0]

