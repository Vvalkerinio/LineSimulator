# RELEASE NOTES 1.1.0a8.36

## Process compliance
- Dodano tolerancję czasu 1e-6 s do klasyfikacji Possible Min/Min/Max/Possible Max.
- Szum float na granicy, np. 229.99999999999994 wobec 230.0, nie generuje już fałszywego HARD_MIN_VIOLATION.
- Rzeczywiste naruszenia większe od tolerancji nadal są raportowane.

## Ulubione miejsce parkingowe manipulatora
- Model manipulatora ma nowe pole preferred_parking_position.
- W zakładce Manipulatory dodano kolumnę Ulubiony parking [ST] w numeracji użytkownika 2..23.
- Wartość jest serializowana w konfiguracji; starsze konfiguracje domyślnie używają pozycji startowej manipulatora.
- EventDriven preferuje ulubiony parking, o ile stanowisko jest aktywne, nieprocesowe, w strefie pracy i nie jest właśnie opuszczonym źródłem.
- Jeśli ulubiony parking jest nielegalny, selektor używa dotychczasowego bezpiecznego fallbacku.
- Walidacja toru, minimalny odstęp i zakaz mijania pozostają bez zmian.

## Debug
- Usunięto spekulacyjne PROCESS_BATH_RETURN drukowane dla każdej odrzuconej próby schedulera.
