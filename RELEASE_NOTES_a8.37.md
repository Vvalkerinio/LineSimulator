# RELEASE NOTES 1.1.0a8.37

## Spójna numeracja użytkownika w zakładce Manipulatory
- Pozycja startowa, Ulubiony parking, Strefa od i Strefa do są wyświetlane jako ST2..ST23.
- Wewnętrzna geometria pozostaje 1..22.
- GUI używa centralnych display_station_id() i internal_station_id().
- Nagłówki zostały oznaczone [ST].

## Walidacja pozycji startowych
- Zmiany manipulatorów są najpierw zbierane i walidowane atomowo.
- Pozycja startowa musi należeć do strefy manipulatora.
- GUI odrzuca pozycje startowe naruszające minimum_manipulator_spacing.
- Przy błędzie konfiguracja nie jest częściowo nadpisywana.

## Shared bath percent
- Zweryfikowano pierwszy wybór ODT w trybie percent=90%: SELECTED 3 AT 0.0 jest prawidłowy.
- Wcześniejsze zatrzymanie nie wynikało z percent. Log wskazywał M1 i M2 na tej samej pozycji wewnętrznej 5, więc pierwszy assignment był blokowany przez track safety.
- Nowa numeracja GUI i walidacja odstępu zapobiegają zapisaniu takiego układu startowego.
