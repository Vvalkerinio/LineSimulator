from copy import deepcopy
from types import SimpleNamespace

import pytest

from src.model.station import Station
from src.optimization import (
    EventDrivenCandidate,
    EventDrivenCandidateApplier,
    EventDrivenCandidateGenerator,
    OptimizationConstraints,
    SharedBathCandidateParameter,
    SharedBathParameterGenerator
)


def configuration():
    stations = [Station(i, f"S{i}", True, i * 10, i * 20)
                for i in range(1, 9)]
    stations[1].shared_bath_group = "ODT"
    stations[2].shared_bath_group = "ODT"
    stations[5].shared_bath_group = "FSF"
    stations[6].shared_bath_group = "FSF"
    for station in stations:
        station.drip_time = float(station.id)
        station.shared_bath_stagger_mode = "percent"
        station.shared_bath_stagger_value = 50.0
    manipulators = [
        SimpleNamespace(id=1, position=1, work_zone_start=1, work_zone_end=2),
        SimpleNamespace(id=2, position=3, work_zone_start=3, work_zone_end=4),
        SimpleNamespace(id=3, position=5, work_zone_start=5, work_zone_end=6),
        SimpleNamespace(id=4, position=7, work_zone_start=7, work_zone_end=8)
    ]
    return SimpleNamespace(
        stations=stations,
        manipulators=manipulators,
        minimum_manipulator_spacing=2
    )


def test_generator_uses_exact_modes_supported_by_selector():
    generator = SharedBathParameterGenerator(
        percent_values=(40, 60), seconds_values=(15,),
        modes=("percent", "seconds", "alternate")
    )
    values = generator.variants_for_group("ODT")
    assert [(item.mode, item.value) for item in values] == [
        ("percent", 40.0), ("percent", 60.0),
        ("seconds", 15.0), ("alternate", 0.0)
    ]


def test_generator_builds_cartesian_variants_for_active_groups():
    variants = list(SharedBathParameterGenerator(
        percent_values=(50,), seconds_values=(), modes=("percent", "alternate")
    ).generate(configuration()))
    assert len(variants) == 4
    assert all({item.group_name for item in variant} == {"ODT", "FSF"}
               for variant in variants)


def test_applier_changes_shared_bath_rule_but_not_process_technology():
    base = configuration()
    before = [(s.min_process_time, s.max_process_time, s.drip_time,
               s.enabled, s.shared_bath_group) for s in base.stations]
    candidate = EventDrivenCandidate(
        (1, 3, 5, 7),
        (
            SharedBathCandidateParameter("ODT", "seconds", 30),
            SharedBathCandidateParameter("FSF", "alternate", 999)
        )
    )
    applied = EventDrivenCandidateApplier().apply(base, candidate)
    after = [(s.min_process_time, s.max_process_time, s.drip_time,
              s.enabled, s.shared_bath_group) for s in applied.stations]
    assert before == after
    assert all(s.shared_bath_stagger_mode == "seconds"
               and s.shared_bath_stagger_value == 30
               for s in applied.stations if s.shared_bath_group == "ODT")
    assert all(s.shared_bath_stagger_mode == "alternate"
               and s.shared_bath_stagger_value == 0
               for s in applied.stations if s.shared_bath_group == "FSF")
    assert base.stations[1].shared_bath_stagger_mode == "percent"


def test_invalid_shared_bath_values_are_rejected():
    with pytest.raises(ValueError):
        SharedBathCandidateParameter("ODT", "percent", 101).normalized()
    with pytest.raises(ValueError):
        SharedBathCandidateParameter("ODT", "seconds", -1).normalized()
    with pytest.raises(ValueError):
        SharedBathCandidateParameter("ODT", "unknown", 1).normalized()


def test_event_candidate_generator_places_current_start_first():
    config = configuration()
    generator = EventDrivenCandidateGenerator(
        OptimizationConstraints(2),
        SharedBathParameterGenerator(
            percent_values=(50,), modes=("percent",)
        )
    )
    first = next(generator.generate(config))
    assert first.start_positions == (1, 3, 5, 7)
    assert {(p.group_name, p.mode, p.value)
            for p in first.shared_bath_parameters} == {
                ("ODT", "percent", 50.0),
                ("FSF", "percent", 50.0)
            }
