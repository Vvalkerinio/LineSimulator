from pathlib import Path
src=Path('src/core/event_driven_simulator.py').read_text()
assert 'actual_time = scheduled.pickup_finish_time - entry_time' in src
assert 'exit_time=scheduled.pickup_finish_time' in src
assert 'actual_time = scheduled.pickup_start_time - entry_time' not in src
