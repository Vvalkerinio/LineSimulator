# RELEASE NOTES 1.1.0a8.27

## Nowa zakładka: Widok linii
- Dodano pełnoekranowy, jednowymiarowy widok linii oparty na wspólnej osi X stanowisk.
- Wszystkie manipulatory są rysowane na jednym torze, dzięki czemu zbliżenia i naruszenia odstępu są widoczne bezpośrednio.
- Wanny, stan obecności zawieszki i czas residence używają dokładnie tej samej transformacji X co manipulatory.
- Widok korzysta z timeline_segments oraz istniejącego resolvera StationAnimationWidget.
- Obsługiwane są wyniki EventDriven i ProgramDriven.

## Animacja i sterowanie
- Odtwarzanie, pauza, początek i suwak czasu.
- Prędkości od 0.25x do 100x.
- Interpolacja pozycji manipulatora w trakcie segmentu.
- Wyświetlanie numeru manipulatora, zawieszki i wskaźnika GÓRA/DÓŁ.
- Kolory wanien odpowiadają stanom czasu procesu używanym w zakładce Trajektorie.
- Szerokość manipulatora korzysta z manipulator_width, domyślnie 2 pozycje.
- Naruszenie wymaganego odstępu jest oznaczane czerwonym łącznikiem i komunikatem KOLIZJA.
