# Line Simulator v1.0

Pierwsza stabilna wersja aplikacji do symulacji linii zawieszkowej.

## Zakres

- EventDriven i ProgramDriven;
- cztery manipulatory na wspólnym torze;
- shared bath;
- programy PLC, adresacja MW i consulty;
- ST23/ST24;
- czas ocieku per stanowisko;
- TrackGuard OFF/WARN/ENFORCE;
- wizualizacja blokad consultów `C<numer> -> M<cel>:<index>`;
- trajektorie z pomiarem A/B;
- throughput pełnych cykli;
- station residence i raporty naruszeń.

## Walidacja

- 105 testów rdzenia zakończonych powodzeniem;
- brak nieużywanych modułów wykrytych przez graf importów;
- brak cache, backupów i jednorazowych patcherów w paczce wydania.
