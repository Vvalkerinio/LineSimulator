$ErrorActionPreference = "Stop"
Write-Host "[1/4] Python"
py --version
Write-Host "[2/4] Compile"
py -m compileall -q src tests
Write-Host "[3/4] Tests"
py -m pytest -q
Write-Host "[4/4] Import smoke test"
$env:QT_QPA_PLATFORM = "offscreen"
py -c "from src.gui.main_window import MainWindow; print('GUI imports OK')"
Write-Host "LinePlanner_M2 v1 validation passed."
