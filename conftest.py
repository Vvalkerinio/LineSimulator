"""Automatic test classification for release validation."""


def pytest_collection_modifyitems(items):
    for item in items:
        path = str(item.fspath).replace("\\", "/")
        name = item.name.lower()
        if "gui" in path or any(
            token in path
            for token in [
                "test_process_tab.py",
                "test_results_tab",
                "test_simulation_tab.py"
            ]
        ):
            item.add_marker("gui")
        else:
            item.add_marker("core")

        if "program_driven" in path or "program_cycle" in path:
            item.add_marker("program_driven")
        if "event_driven" in path:
            item.add_marker("event_driven")
