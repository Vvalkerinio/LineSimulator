# Line Simulator v1.1.0a8.21

## Postęp symulacji
- Dodano pasek postępu 0-100% w zakładce symulacji.
- Pasek pokazuje czas symulowany, limit czasu oraz liczbę przetworzonych zdarzeń.
- EventDrivenSimulator udostępnia opcjonalny progress_callback.
- Aktualizacje są ograniczone do zmiany pełnego procentu, aby nie obciążać gorącej pętli.
- GUI jest odświeżane podczas symulacji przez QApplication.processEvents().

## Ręczna edycja programu PLC
- Dodano przycisk `Dodaj nowy krok`.
- Pierwszy krok można dodać także do pustego programu.
- Przy braku programu użytkownik wybiera manipulator M1-M4, a program zostaje utworzony z aktualnym adresem indeksu, offsetem i station_id_shift.
- Dotychczasowy przycisk `Dodaj krok po zaznaczonym` nadal kopiuje zaznaczony krok.

## Sekwencja przeładunku
- Dodano przycisk `Dodaj sekwencję przeładunku`.
- Przycisk wstawia trzy kroki po zaznaczonym kroku albo na końcu programu:
  1. ST23 DROP
  2. ST24 PICKUP
  3. ST22 DROP
- Czasy WAIT są pobierane z istniejących ustawień przeładunku.

## Stanowisko i offset PLC
- Tabela programu PLC ma 12 kolumn.
- Dodano edytowalną kolumnę `Stanowisko` bez offsetu.
- `Stanowisko PLC` jest wyliczane automatycznie według wzoru:
  `station_id - station_offset + station_id_shift`.
- Kolumna `Stanowisko PLC` jest tylko do odczytu.
- Zaktualizowano indeksy kolumn Akcja, WAIT, Komenda, Źródło, Cel i Status.

## Walidacja
- compileall: PASS
- testy GUI i regresja zakresu zmiany: 28 passed, 0 failed
- testy są statyczne dla GUI, ponieważ środowisko CI nie zawiera PySide6.
- baza a8.20 przed zmianą: 265 passed, 0 failed
