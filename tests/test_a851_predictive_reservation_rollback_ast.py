from pathlib import Path


def test_failed_predictive_commit_rolls_back_selected_manipulator_reservation():
    source = Path('src/core/event_driven_simulator.py').read_text()
    assert 'availability_before = dict(' in source
    assert 'previous_busy = availability_before.get(manipulator_id)' in source
    assert 'availability.reserve(manipulator_id, previous_busy)' in source
