# Line Simulator v1.1.0a8.17

## Teoretyczna wydajność

- nominalny i possible certified upper bound,
- pojemność wanien i grup shared bath,
- idealny limit puli manipulatorów,
- obowiązkowe obciążenie M1-M4,
- diagnostyka interfejsów M1/M2, M2/M3, M3/M4,
- automatyczny raport po EventDriven,
- porównanie z osiągniętym throughput i luka do granicy.

## Twarde strefy pracy

- usunięto `strict_work_zone`, `zone_penalty` i całą logikę punktacji poza strefą,
- źródło i cel transportu muszą znajdować się w strefie manipulatora,
- GUI manipulatorów ma 7 kolumn,
- nowe JSON nie zapisują usuniętych pól,
- stare JSON z tymi polami nadal są odczytywane, a klucze są ignorowane.

## Walidacja

- 245 passed, 0 failed,
- compileall: PASS.
