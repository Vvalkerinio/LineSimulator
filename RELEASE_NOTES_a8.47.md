# RELEASE NOTES 1.1.0a8.47

## Deferred transport cleanup
- Naprawiono KeyError w wake_deferred_transports po udanym commit transportu odroczonego.
- commit_scheduled_transport może usunąć hanger z deferred_transports, dlatego wake używa idempotentnego pop(hanger_id, None) zamiast del.
- Obsługa jest bezpieczna także przy zagnieżdżonych wake-up z TRANSPORT_END i QUEUE_RELEASE.
- Dodano test regresyjny blokujący ponowne wprowadzenie del deferred_transports[hanger_id].

## Reprodukcja użytkownika
- default config,
- jedyna zmiana: strefa M1 widoczna ST2..ST7, wewnętrzna 1..6,
- ODT alternate 80,
- feed 3600 s.
Symulacja kończy się bez wyjątku, bez deadlocka, bez deferred i z Separation OK.
