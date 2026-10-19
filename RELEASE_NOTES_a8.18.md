# Line Simulator v1.1.0a8.18

## Nowy tryb optymalizacji

Dodano dwa wybieralne tryby:

1. `Pełny EventDriven`
   - każdy kandydat przechodzi pełną symulację EventDriven,
   - domyślny limit: 500 kandydatów.

2. `Theoretical screening -> EventDriven finał`
   - wszystkie kandydatury są najpierw oceniane analitycznie,
   - EventDriven uruchamia się wyłącznie dla finalistów,
   - domyślny limit: 5000 kandydatów,
   - domyślna liczba finalistów: 20.

## Screening theoretical

Ocena kandydata uwzględnia:

- nominalny certified upper bound,
- possible certified upper bound,
- limiting resource,
- minimalny koszt dojścia manipulatorów do pierwszych legalnych zadań,
- odległość pozycji startowych od środka stref,
- margines minimalnego odstępu manipulatorów,
- proxy ustawień shared bath.

Finaliści są dywersyfikowani według pozycji startowych i ustawień shared bath.
Wiersz `THEORETICAL_CANDIDATE` nie może zostać zastosowany. Zastosować można
wyłącznie `VALID EVENT_CANDIDATE` po pełnej walidacji EventDriven.

## GUI i eksport

- wybór trybu w zakładce Optymalizacja,
- pole liczby finalistów widoczne tylko w trybie theoretical,
- wartości analityczne w tabeli oznaczone prefiksem `UB`,
- podgląd pokazuje metryki screeningu i rangę theoretical,
- CSV zawiera metryki theoretical i EventDriven.

## Walidacja

- 257 passed, 0 failed,
- compileall: PASS.
