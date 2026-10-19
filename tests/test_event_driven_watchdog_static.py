from pathlib import Path


def test_event_simulator_has_retry_and_global_watchdogs():
    source = Path("src/core/event_driven_simulator.py").read_text()
    assert "event_driven_max_shared_bath_retries" in source
    assert "SHARED_BATH_RETRY_LIMIT" in source
    assert "event_driven_max_events" in source
    assert "event_driven_max_time" in source
    assert "EVENT_DRIVEN_WATCHDOG" in source


def test_optimizer_suppresses_verbose_event_console_output():
    source = Path(
        "src/optimization/event_driven_candidate_evaluator.py"
    ).read_text()
    assert "synchronized_suppress_stdout" in source
    assert "os.devnull" not in source
    assert "event_watchdog_triggered" in source
