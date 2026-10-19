from types import SimpleNamespace

from src.optimization.configuration_clone import clone_configuration_for_candidate


def test_candidate_clone_isolates_runtime_objects_and_top_level_containers():
    station = SimpleNamespace(id=1, runtime_marker=0)
    manipulator = SimpleNamespace(id=1, position=4)
    source = SimpleNamespace(stations=[station], manipulators=[manipulator], program_index_addresses={1: 500}, shared_bath_groups=["A"])
    cloned = clone_configuration_for_candidate(source)
    cloned.stations[0].runtime_marker = 9
    cloned.manipulators[0].position = 7
    cloned.program_index_addresses[1] = 600
    cloned.shared_bath_groups.append("B")
    assert source.stations[0].runtime_marker == 0
    assert source.manipulators[0].position == 4
    assert source.program_index_addresses == {1: 500}
    assert source.shared_bath_groups == ["A"]
