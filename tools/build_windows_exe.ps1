$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ProjectRoot

Write-Host "[1/5] Tworzenie srodowiska build"
if (-not (Test-Path ".venv-build")) {
    py -3.12 -m venv .venv-build
}

$Python = Join-Path $ProjectRoot ".venv-build\Scripts\python.exe"

Write-Host "[2/5] Instalacja zaleznosci"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements-build.txt

Write-Host "[3/5] Testy i kompilacja"
& $Python -m compileall -q src tests
& $Python -m pytest -q

Write-Host "[4/5] Budowanie EXE"
Remove-Item build, dist -Recurse -Force -ErrorAction SilentlyContinue
& $Python -m PyInstaller --noconfirm --clean LineSimulator.spec

$Exe = Join-Path $ProjectRoot "dist\Line Simulator v1.0.exe"
if (-not (Test-Path $Exe)) {
    throw "Nie utworzono pliku: $Exe"
}

Write-Host "[5/5] SHA256"
Get-FileHash $Exe -Algorithm SHA256 |
    Format-List |
    Out-File "dist\Line Simulator v1.0.sha256.txt" -Encoding utf8

Write-Host "Gotowe: $Exe"
