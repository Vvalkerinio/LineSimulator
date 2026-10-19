from types import SimpleNamespace

from src.optimization import (
    EventDrivenCandidateGenerator, OptimizationConstraints,
    SharedBathParameterGenerator
)


def configuration():
    stations = [
        SimpleNamespace(id=3, enabled=True, shared_bath_group="ODT",
                        shared_bath_stagger_mode="percent",
                        shared_bath_stagger_value=50.0),
        SimpleNamespace(id=4, enabled=True, shared_bath_group="ODT",
                        shared_bath_stagger_mode="percent",
                        shared_bath_stagger_value=50.0)
    ]
    refs = (4, 11, 16, 22)
    manipulators = [
        SimpleNamespace(id=index + 1, position=value,
                        work_zone_start=max(1, value - 2),
                        work_zone_end=min(22, value + 2))
        for index, value in enumerate(refs)
    ]
    return SimpleNamespace(stations=stations, manipulators=manipulators)


def generator():
    return EventDrivenCandidateGenerator(
        OptimizationConstraints(2),
        SharedBathParameterGenerator(
            percent_values=(30, 40, 50, 60, 70),
            seconds_values=(0, 15, 30),
            modes=("percent", "seconds", "alternate")
        )
    )


def distance(candidate):
    return sum(abs(a-b) for a, b in zip(
        candidate.start_positions, (4, 11, 16, 22)
    ))


def test_exact_reference_is_first_then_only_smallest_total_changes():
    values = list(generator().generate(configuration()))[:20]
    assert values[0].start_positions == (4, 11, 16, 22)
    assert values[0].shared_bath_parameters[0].value == 50.0
    # After reference, candidates at total distance 1 precede distance 2+.
    scores = []
    for item in values:
        shared = item.shared_bath_parameters[0]
        shared_distance = (
            abs(shared.value - 50.0) / 10.0
            if shared.mode == "percent" else 4.0
        )
        scores.append(distance(item) + shared_distance)
    assert scores == sorted(scores)
    assert all(score <= 2.0 for score in scores[:10])


def test_mode_changes_are_deferred_after_near_numeric_changes():
    values = list(generator().generate(configuration()))[:80]
    changed = [
        index for index, item in enumerate(values)
        if item.shared_bath_parameters[0].mode != "percent"
    ]
    assert not changed or changed[0] > 10
