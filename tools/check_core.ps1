$ErrorActionPreference = "Stop"
py -m compileall -q src tests
py -m pytest -q `
  --ignore=tests/test_gui_imports.py `
  --ignore=tests/test_process_tab.py `
  --ignore=tests/test_results_tab.py `
  --ignore=tests/test_results_tab_extended.py `
  --ignore=tests/test_results_tab_warning_panel.py `
  --ignore=tests/test_simulation_tab.py
