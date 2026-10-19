# RELEASE NOTES 1.1.0a8.34

## Naprawa EventDriven parking po process bath uruchamianego z GUI
- Zakładka Symulacja tworzyła SimulationServicesFactory bez listy stanowisk.
- AssignmentSelector otrzymywał pustą station_map.
- ODT nie było rozpoznawane jako process bath.
- Nie wykonywała się logika PROCESS_BATH_RETURN.
- M1 pozostawał nad wanną ODT mimo aktywnego stanowiska nieprocesowego w strefie.
- GUI przekazuje teraz configuration.stations do SimulationServicesFactory.
