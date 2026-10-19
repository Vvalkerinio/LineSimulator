# RELEASE NOTES 1.1.0a8.24

## Optymalizacja ewaluacji kandydatow
- Zastapiono pelne `deepcopy` konfiguracji w `ProgramCandidateEvaluator` i `EventDrivenCandidateApplier` dedykowanym klonowaniem stanu kandydata.
- Klonowane sa obiekty konfiguracji, stanowisk i manipulatorow oraz mutowalne kontenery najwyzszego poziomu.
- Zachowano izolacje pozycji manipulatorow i stanow runtime shared bath miedzy kandydatami.

## MaterialCycleWindowFinder
- Dodano cache wynikow `_candidate` dla identycznych granic okna i parametrow seed.
- Cache zwraca izolowana kopie listy komunikatow, aby dopiski wywolujacego nie zmienialy wpisu cache.
- Dodano liczniki `candidate_cache_stats`: hits, misses i size do profilowania.

## Profilowanie
- Mikrobenchmark 20 000 klonowan konfiguracji 22 stanowisk i 4 manipulatorow:
  - `deepcopy`: 18.832549 s
  - dedykowane klonowanie: 2.482012 s
  - przyspieszenie tej operacji: 7.59x
- Wynik dotyczy kosztu klonowania, nie czasu pelnej symulacji.
