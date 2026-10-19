# Line Simulator 1.1.0a8.55

## Naprawa generowania zawieszek
- Usunięto globalny limiter WIP wprowadzony w a8.54 w obsłudze HANGER_ENTRY.
- Usunięty limiter wielokrotnie przekładał każde wejście (`ENTRY_ADMISSION_DEFERRED`) i powodował w GUI wrażenie, że zawieszki się nie generują.
- Wejścia ponownie używają fizycznej kolejki stanowiska załadunku i istniejących zdarzeń ENTRY_RELEASE.

## Parking / YIELD
- Zachowano poprawkę: transport produkcyjny kończy się na DROP.
- Parking nie jest automatycznym `return_move` transportu.
- YIELD pozostaje osobnym ruchem oraz zachowuje `propose()` / `commit()`.

## Test akceptacyjny
- default.json
- ODT percent 50%
- M1 display zone ST2..ST7 (internal 1..6)
- M1 parking ST6 (internal 5)
- infinite feed 3600 s

Wynik: 61 zawieszek z zadaniami, 610 zadań, 0 deadlocków, 0 deferred, separation OK, minimum distance 2.0.

Uwaga: konfiguracja percent 50% nadal tworzy 346 HARD_MAX_VIOLATION. Ta wersja naprawia generowanie, crash/deadlock i kolizję parking/YIELD; nie ukrywa naruszeń procesu.
