# RELEASE NOTES 1.1.0a8.31

## Globalna ochrona wanien procesowych w EventDriven
- EventDriven przekazuje pełną listę stanowisk do SimulationServicesFactory i AssignmentSelector.
- Po DROP nad aktywną wanną procesową selektor planuje return_move do najbliższego aktywnego stanowiska nieprocesowego w strefie manipulatora.
- Stanowisko źródłowe właśnie zakończonego transportu jest wykluczane z parkingu. Chroni to pozycję załadunku po sekwencji LOAD -> ODT.
- Kandydaci są wybierani deterministycznie według odległości od celu, odległości od pozycji domowej oraz ID.
- Ruch powrotny nadal przechodzi istniejącą walidację toru, rezerwację, brak mijania i minimalny odstęp.
- Pozostanie nad wanną procesową jest dozwolone wyłącznie, gdy w strefie nie ma aktywnego stanowiska nieprocesowego.
- Dodano diagnostykę PROCESS_BATH_RETURN oraz PROCESS_BATH_PARKING_FALLBACK.

## ODT shared bath
- Dodano regresję dla obu wewnętrznych stanowisk ODT 3 i 4.
- Shared bath nie otrzymuje wyjątku nazwowego. Ochrona działa dla każdej stacji z is_process_bath=true.
