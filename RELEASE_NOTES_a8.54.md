# Line Simulator 1.1.0a8.54

## Parking / YIELD / scheduler
- Usunięto implicit return_move do parkingu z końca transportu produkcyjnego.
- Transport kończy się na DROP; ewentualny YIELD jest osobno proponowany i commitowany przez EventTrackYieldPlanner.
- Dodano pressure-aware admission: wejście nowej zawieszki jest wstrzymywane przy deferred transport oraz po osiągnięciu bezpiecznego WIP=2 (konfigurowalne przez event_driven_max_wip).
- Chroni to tor przed kolizją powodowaną przez przyszły return_move do pozycji zajmowanej przez sąsiedni manipulator.

## Test akceptacyjny
Default, ODT percent 50%, M1 display zone ST2..ST7, M1 parking ST6.
Wynik: brak wyjątku, deadlocks=0, separation=OK, minimum distance=2.0, deferred=0.
Pozostaje jedno naruszenie procesu H2 internal S6: 152.0 s przy Possible Max 90.0 s; nie jest ukrywane ani deklarowane jako naprawione.
