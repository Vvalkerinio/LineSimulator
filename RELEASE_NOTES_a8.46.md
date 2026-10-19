# RELEASE NOTES 1.1.0a8.46

## Idempotent lifecycle transportu EventDriven
- Jedna para hanger/source może mieć tylko jeden aktywny transport.
- Wielokrotne PROCESS_END, predictive retry, deferred wake i QUEUE_RELEASE nie mogą ponownie zatwierdzić tej samej operacji fizycznej.
- Commit sprawdza, czy zawieszka nadal fizycznie znajduje się na deklarowanym stanowisku źródłowym.
- TRANSPORT_END jest idempotentny i nie może drugi raz zwiększyć route_index.
- Deferred transport jest usuwany natychmiast po poprawnym commit.
- PROCESS_END nie planuje ponownie transportu aktywnego, ukończonego ani oczekującego w deferred.

## Skutek
Usunięto sekwencję, w której H2 wykonywał 6->8 dwa razy, route_index przeskakiwał o dwa, a następnie powstawał nielegalny transport 15->20 i stały GROUP_OCCUPIED retry loop.
