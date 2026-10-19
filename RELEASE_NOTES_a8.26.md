# RELEASE NOTES 1.1.0a8.26

## Station Residence Time Report
- Dodano pełne rozbicie statusów compliance: TradeMin, TradeMax, HardMin i HardMax.
- Dodano HardTotal na stację oraz ProcessViolations w podsumowaniu.
- ProcessViolations jest liczone jako HardMin + HardMax, zgodnie z zakładką Wyniki.
- Lista TOP 10 pokazuje teraz kompromisy i twarde naruszenia, wraz z zakresem Possible i Nominal.
- Numery stanowisk w raporcie używają numeracji użytkownika.

## Audyt opcji Wanna procesowa
- Potwierdzono zapis/odczyt is_process_bath w konfiguracji i obsługę checkboxa GUI.
- ParkingPositionSelector preferuje stanowiska nieprocesowe i używa procesowego tylko jako fallback.
- TrajectoryAwarePrepositionPlanner całkowicie odrzuca stanowiska procesowe dla planowanego prepositioningu.
- Ustalono lukę: EventDriven i konwersja jego segmentów do PLC nie mają centralnej reguły zabraniającej długiego bezczynnego postoju nad wanną procesową. Flaga nie jest globalnym ograniczeniem runtime.
