# RELEASE NOTES 1.1.0a8.33

## Naprawa zawieszenia dla czasu ruchu 4.3 s/pozycję
- Przebudowano SegmentBuilder tak, aby poprawnie obsługiwał interpolowane pozycje zmiennoprzecinkowe.
- Usunięto pętlę opartą na dokładnym porównaniu float `current_position != target_station`.
- Rezerwacje toru są teraz budowane według kolejnych granic pozycji i mają matematycznie ograniczoną liczbę iteracji.
- Pierwszy i ostatni segment mogą być częściowe, a ich czas jest proporcjonalny do faktycznie pokonanego dystansu.
- Pozycje bardzo bliskie liczbie całkowitej są normalizowane z tolerancją 1e-9.
- Dodano walidację NaN/Inf, ujemnego czasu ruchu oraz ochronę braku postępu.
- Zmiana nie ogranicza czasu ruchu do wielokrotności 0.5 s.

## Regresje
- Dodano testy ruchu 3.7 -> 5.0 oraz 5.0 -> 3.7 przy 4.3 s/pozycję.
- Dodano test pozycji 3.9999999999999996 -> 5.0.
- Potwierdzono zakończenie pełnego scenariusza EventDriven dla 4.3 i 4.5 s/pozycję.
