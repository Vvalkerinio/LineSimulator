# Line Simulator v1.1.0a8.22

## Ilość sztuk na transport
- Dodano parametr `pieces_per_transport` do SimulationConfiguration.
- Domyślna wartość: 7.
- Pole `Ilość sztuk na transport` jest dostępne w zakładce Symulacja.
- Parametr jest zapisywany i odczytywany z JSON.
- Starsze konfiguracje bez pola otrzymują wartość 7.

## Precise Event Throughput
- `transports_per_hour` oznacza liczbę fizycznych wyjść zawieszek na godzinę.
- `parts_per_hour = transports_per_hour * pieces_per_transport`.
- EventDriven i ProgramDriven używają interwałów pomiędzy HANGER_EXIT.
- Liczba komend transportowych wewnątrz cyklu PLC nie zawyża throughput.
- Starszy wynik ProgramDriven bez zdarzeń HANGER_EXIT zachowuje cycle throughput jako fallback.

## Cycle Time
- Cycle Time jest średnim interwałem pomiędzy kolejnymi HANGER_EXIT.

## Zakładka Wyniki
Górny widget KPI zawiera tylko:
- Precise Event Throughput - Ilość szt/h,
- Precise Event Throughput - Ilość transportów/h,
- Cycle Time [s],
- Process Violations,
- Manipulator Separation: OK/NOK.

Dotychczasowe metryki zostały przeniesione do widgetu `Szczegóły symulacji`.

## Czas w wannie i Max Violations
- EventDriven kończy czas przebywania w wannie w chwili rozpoczęcia podnoszenia.
- Poprzednio używany był koniec podnoszenia, co doliczało lift_time.
- ProgramDriven już wcześniej używał początku pickup, więc oba silniki są teraz zgodne.

## Walidacja
- compileall: PASS
- regresja backendu: 276 passed, 0 failed
- testy GUI wymagające PySide6 pozostają wyłączone w profilu backendowym
