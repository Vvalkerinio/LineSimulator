from copy import deepcopy
from types import SimpleNamespace

from src.model.event_type import EventType
from src.model.station import Station
from src.optimization import (
    EventDrivenCandidate,
    EventDrivenCandidateEvaluator,
    SharedBathCandidateParameter
)


class Compliance:
    def __init__(self, min_ok=True, max_ok=True):
        self.min_ok = min_ok
        self.max_ok = max_ok


class Event:
    def __init__(self, target, event_type=EventType.TRANSPORT_END):
        self.target_station = target
        self.event_type = event_type


def configuration():
    stations = [Station(i, f"S{i}", True, 0, 100) for i in range(1, 9)]
    stations[1].shared_bath_group = "ODT"
    stations[2].shared_bath_group = "ODT"
    for station in stations:
        station.drip_time = 0.0
        station.shared_bath_stagger_mode = "percent"
        station.shared_bath_stagger_value = 50.0
    manipulators = [SimpleNamespace(id=i, position=2 * i - 1)
                    for i in range(1, 5)]
    return SimpleNamespace(stations=stations, manipulators=manipulators)


def candidate(group="ODT"):
    return EventDrivenCandidate(
        (1, 3, 5, 7),
        (SharedBathCandidateParameter(group, "percent", 40),)
    )


def result(min_ok=True, max_ok=True, deadlocks=None, completed=10):
    return SimpleNamespace(
        final_time=100.0,
        processed_events=50,
        scheduled_transports=12,
        completed_transports=completed,
        deadlocks=list(deadlocks or []),
        process_violations=[],
        process_compliance=[Compliance(min_ok, max_ok)],
        events=[Event(2), Event(2), Event(3)],
        steady_state={
            "detected": True,
            "throughput": 420.0,
            "reason": "test"
        }
    )


def simulator_factory(fake_result, captured):
    class FakeSimulator:
        def __init__(self, config):
            captured.append(config)
        def run(self):
            return fake_result
    return FakeSimulator


def test_valid_event_candidate_returns_metrics_and_shared_bath_usage():
    captured = []
    evaluator = EventDrivenCandidateEvaluator(
        configuration(),
        simulator_factory=simulator_factory(result(), captured)
    )
    evaluated = evaluator(candidate())
    assert evaluated.status == "VALID"
    assert evaluated.metrics["event_throughput_per_hour"] == 420.0
    assert evaluated.metrics["shared_bath_usage"] == {
        "ODT": {2: 2, 3: 1}
    }
    assert captured[0].stations[1].shared_bath_stagger_value == 40.0


def test_residence_and_deadlock_reject_event_candidate():
    evaluator = EventDrivenCandidateEvaluator(
        configuration(),
        simulator_factory=simulator_factory(
            result(min_ok=False, max_ok=False, deadlocks=["x"]), []
        )
    )
    evaluated = evaluator(candidate())
    assert evaluated.status == "REJECTED"
    assert set(evaluated.rejection_reasons) == {
        "EVENT_DEADLOCK",
        "EVENT_MIN_RESIDENCE",
        "EVENT_MAX_RESIDENCE"
    }


def test_zero_completed_transport_with_positive_steady_throughput_is_valid():
    evaluator = EventDrivenCandidateEvaluator(
        configuration(),
        simulator_factory=simulator_factory(result(completed=0), [])
    )
    evaluated = evaluator(candidate())
    assert evaluated.status == "VALID"
    assert "EVENT_NO_COMPLETED_TRANSPORT" not in evaluated.rejection_reasons


def test_invalid_group_is_rejected_without_running_simulator():
    called = []
    evaluator = EventDrivenCandidateEvaluator(
        configuration(),
        simulator_factory=lambda config: called.append(config)
    )
    evaluated = evaluator(candidate(group="MISSING"))
    assert evaluated.status == "REJECTED"
    assert evaluated.rejection_reasons == ("EVENT_INVALID_CANDIDATE",)
    assert called == []


def test_base_configuration_is_not_mutated():
    base = configuration()
    evaluator = EventDrivenCandidateEvaluator(
        base, simulator_factory=simulator_factory(result(), [])
    )
    evaluator(candidate())
    assert base.stations[1].shared_bath_stagger_value == 50.0
    assert [item.position for item in base.manipulators] == [1, 3, 5, 7]
