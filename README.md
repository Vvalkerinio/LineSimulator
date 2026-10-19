# Line Simulator v1.0

Aplikacja do planowania i symulacji automatycznej linii transportu zawieszek z czterema manipulatorami.

## Wymagania

- Python 3.12
- Windows 10/11
- zależności z `requirements.txt`

## Instalacja

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

## Uruchomienie

```powershell
py -m src.gui.app
```

## Kontrola jakości

```powershell
py -m compileall -q src tests
.\tools\check_core.ps1
.\tools\check_v1.ps1
```

## Najważniejsze funkcje

- symulacja EventDriven i ProgramDriven;
- konfiguracja 22 stanowisk bazowych i 4 manipulatorów;
- shared bath i kontrola czasów min/max;
- program PLC, import/eksport TXT i edytor consultów;
- wirtualny przeładunek ST23/ST24 w ProgramDriven;
- czasy ocieku per stanowisko;
- TrackGuard OFF/WARN/ENFORCE;
- trajektorie, indeksy PLC i pomiar czasu A/B;
- KPI oraz raport residence time.

## Struktura

- `src/model` modele danych;
- `src/core` silniki i logika wykonawcza;
- `src/analysis` generatory, KPI i raporty;
- `src/io` zapis/odczyt konfiguracji;
- `src/gui` interfejs PySide6;
- `tests` testy;
- `examples` przykładowe programy i consulty;
- `docs` audyt oraz checklista wydania.

## Status

Stabilna wersja `1.0.0`. Historia przygotowania wydania znajduje się w `docs/V1_AUDIT.md`.


## Budowanie wersji Windows EXE

Na komputerze Windows z Pythonem 3.12:

```powershell
.\tools\build_windows_exe.ps1
```

Gotowy program zostanie zapisany jako:

```text
dist\Line Simulator v1.0.exe
```
