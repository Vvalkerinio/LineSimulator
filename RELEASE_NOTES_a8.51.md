# Line Simulator 1.1.0a8.51

## Predictive pickup po shared bath
- Cofanie spekulacyjnej rezerwacji wybranego manipulatora, gdy końcowa walidacja toru odrzuci zaplanowany predictive pickup.
- Rezerwacje YIELD innych manipulatorów pozostają aktywne.
- Deferred predictive pickup ma ready_at równy zakończeniu wszystkich aktywnych YIELD powstałych w danej próbie.
- Wake-up przed ready_at nie ponawia harmonogramowania.
- Retry jest planowany dokładnie na zakończenie YIELD, a 30 s pozostaje fallbackiem.

## Naprawiony przypadek
Konfiguracja bazowa, M1 ST2..ST7, ODT alternate 80, feed 3600 s. W a8.50 H2 na wewnętrznym S6 pozostawał 134 s przy Possible Max 90 s. W a8.51 wszystkie 610 operacji mają status OK.
