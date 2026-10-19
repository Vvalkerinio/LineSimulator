# LinePlanner_M2 v1.0 - audyt repozytorium

## Wynik bazowy

- 503 pliki w paczce wejściowej.
- 243 pliki Python.
- 225 plików `.pyc` i 8 katalogów `__pycache__`.
- `python -m compileall -q src`: PASS.
- Pełny pytest w środowisku audytowym: blokada kolekcji z powodu braku PySide6 w pierwotnym `requirements.txt`.
- Testy bez GUI: 76 PASS, 10 FAIL.

## Blokery v1.0

1. `requirements.txt` zawierał tylko `pytest`, mimo bezpośrednich importów PySide6 i matplotlib.
2. 10 testów bez GUI nie przechodzi:
   - testy starszego `ManipulatorSelector` oczekują `Manipulator.total_transport_time`, którego aktualny model nie ma;
   - test importera TXT używa starego argumentu `start_addresses_by_manipulator`;
   - test `SimulationConfiguration()` zakłada konstruktor bez obowiązkowych stations/manipulators;
   - część starszych testów EventDriven nie odpowiada aktualnemu kontraktowi silnika.
3. W repo były kopie `src/*/backup`, jednorazowe patchery i zrzuty całego kodu.
4. Pięć największych aktywnych modułów przekracza 49 kB; GUI i symulatory wymagają refaktoru po zamrożeniu testów regresyjnych.

## Bezpiecznie usunięte w kandydacie

- `.pytest_cache/`, wszystkie `__pycache__/`, `.pyc`, `.pyo`.
- `src/gui/backup/`, `src/analysis/backup/`.
- jednorazowe skrypty `fix_*.py` i `patch_*.py` z katalogu głównego, bez referencji w src/tests/main.py.
- `repo_source_dump*.txt`, `repo_files.txt`.

## Przeniesione

- ręczne próbki programów PLC do `examples/plc/`;
- ręczne próbki consultów do `examples/consults/`;
- aktywne `manipulator_program.txt` i `manipulator_consults.txt` pozostawiono w root, ponieważ są referencjonowane przez kod/testy.

## Kandydaci do dalszego potwierdzenia przed usunięciem

Analiza statyczna nie wykazała importów dla:

- `src/analysis/collision_candidate.py`
- `src/analysis/consult_resolution.py`
- `src/core/predictive_preposition_service.py`
- `src/core/shared_bath_lookup.py`
- `src/core/shared_bath_route_compressor.py`
- `src/core/shared_bath_stagger_policy.py`
- `src/model/manipulator_program_runtime.py`
- `src/model/process_violation_engine.py`
- `src/model/program_step_execution.py`
- `src/model/recipe_route.py`
- `src/model/routing_request.py`

Nie zostały usunięte, ponieważ mogą być elementami planowanej architektury lub kodu uruchamianego pośrednio.

## Plan commitów

1. `chore: remove generated files and backups`
2. `build: declare runtime dependencies and gitignore`
3. `test: classify and repair outdated tests`
4. `test: add ProgramDriven v1 regression suite`
5. `refactor: split CyclogramTab controllers`
6. `refactor: split ProgramDrivenSimulator services`
7. `docs: add README and v1 release checklist`
8. `release: v1.0.0`

## Bramka wydania

- `python -m compileall -q src tests`
- `python -m pytest -q`
- ręczny smoke test GUI
- zapis/odczyt konfiguracji
- EventDriven i ProgramDriven
- import/eksport PLC i consultów
- ST23/ST24, drip time, TrackGuard OFF/WARN/ENFORCE
- throughput pełnego cyklu i station residence

## Etap 2 wykonany

- Usunięto potwierdzony legacy `src/gui/program_trajectory_tab.py`.
- Usunięto martwy parametr i callback `program_trajectory_tab` z `CyclogramTab`.
- Naprawiono `ManipulatorSelector`: aktualne API `transport_time`, ochrona pustego managera.
- Zaktualizowano dwa historyczne testy do aktualnych kontraktów importera i konfiguracji.

## Etap 3 wykonany

- Dodano `README.md`, wersję pakietu `1.0.0rc1` i konfigurację markerów pytest.
- Dodano `Manipulator.pickup_travel_time`, zgodny z aktualnym modelem położenia.
- Stan testów bez GUI po etapie 2: 80 PASS, 6 FAIL.
- Pozostałe 5 historycznych testów EventDriven i 1 test kolizji wymagają decyzji o aktualnym kontrakcie, dlatego nie zmieniono logiki produkcyjnej tylko po to, aby wymusić zielony test.

## Etap 4 wykonany

- Zaktualizowano historyczne testy EventDriven do `EventType` enum.
- Uzgodniono test `AssignmentSelector` z aktualnym kontraktem najwcześniejszego wykonalnego przydziału.
- Uzgodniono test shared bath z bieżącym deterministycznym wyborem równoważnych kandydatów.
- Dodano regresję throughput: 2 zawieszki / 865 s = 8.3237 szt/h.
- Dodano regresję TrackGuard OFF/WARN/ENFORCE.
- Dodano regresję importu programu od MW Index wpisanego w GUI.

## Wynik etapu 4

Testy rdzenia bez modułów wymagających PySide6:

```text
90 passed
0 failed
```

Dodano `tools/check_core.ps1` i `tools/check_v1.ps1` do walidacji na Windows.

## Etap 5 wykonany

- Wydzielono obliczenia KPI cyklu do `src/analysis/program_cycle_kpi.py`.
- `ProgramDrivenSimulator` zachowuje kompatybilny wrapper, ale nie zawiera już algorytmu KPI.
- Dodano automatyczne markery pytest: core, gui, program_driven, event_driven.
- Dodano testy kontraktu nowego serwisu KPI.

### Wynik testów etapu 5

`94 passed, 0 failed` dla testów rdzenia. Algorytm KPI został przeniesiony z symulatora do osobnego serwisu. Rozmiar `program_driven_simulator.py`: 84074 B; nowy serwis KPI: 4888 B.

## Etap 6 wykonany

- Utworzono `src/core/program_track_guard.py`.
- Wydzielono normalizację OFF/WARN/ENFORCE, budowanie rekordów konfliktu i decyzję o oczekiwaniu.
- `ProgramDrivenSimulator` zachowuje kompatybilne wrappery `_track_guard_mode`, `_track_guard_record` i `_apply_track_safety_guard`.
- Geometria konfliktów pozostaje chwilowo w symulatorze i jest przekazywana do serwisu jako callback. To ogranicza zakres refaktoru bez zmiany zachowania.
- Dodano testy serwisu dla OFF, WARN i ENFORCE.

## Etap 7 wykonany

- Wydzielono geometrię TrackGuard do `src/core/program_track_conflict_detector.py`.
- Detektor odpowiada za interpolację pozycji, minimalny dystans segmentów i wybór najpóźniej kończącego się konfliktu.
- `ProgramTrackGuard` zawiera wyłącznie politykę OFF/WARN/ENFORCE.
- `ProgramDrivenSimulator` zachowuje kompatybilne wrappery metod geometrii.
- Dodano niezależne testy interpolacji, braku nakładania, przecięcia i wyboru konfliktu.

### Optymalizacja detektora konfliktów

Dodano szybkie odrzucanie segmentów o rozłącznych obwiedniach przestrzennych. Dokładne wyliczenie minimalnego dystansu jest wykonywane tylko dla segmentów, które nakładają się czasowo i mogą zbliżyć się do siebie na wymagany odstęp.


## Etap 8 wykonany

- Wydzielono `ProgramConsultSynchronizer` do `src/core/program_consult_synchronizer.py`.
- Consulty są indeksowane po `(source_manipulator_id, source_plc_index)`, zamiast skanowania całej listy przy każdym słowie PLC.
- Symulator zapisuje `result.consult_waits` z numerem consultu, źródłowym i docelowym indeksem, pozycją, czasem początku, końca i trwania.
- Zakładka Trajektorie rysuje okres oczekiwania na consult grubą czerwoną linią.
- Etykieta ma format `C<numer> → M<cel>:<index>`, np. `C3 → M2:15`.
- Tooltip zawiera pełną zależność i czas blokady.


## Etap 9 wykonany: usuwanie nieużywanych pozostałości

Usunięto moduły nieosiągalne z punktów wejścia aplikacji i nieużywane przez testy. Pełna lista znajduje się w `docs/REMOVED_UNUSED_FILES.md`. Po usunięciu ponownie wykonano analizę importów, kompilację i testy rdzenia.


## Korekta interfejsu i audytu residence

- Usunięto pustą zakładkę `Trasa` oraz nieużywaną metodę `_create_route_tab`.
- W zakładce `Trajektorie` wykres i panel czasów wanien są rozdzielone pionowym `QSplitter`; wysokość można zmieniać przeciągając uchwyt.
- Ukrycie panelu zapamiętuje jego ostatnią wysokość, a ponowne pokazanie ją przywraca.
- Dodano fail-fast `ProgramResidenceAuditor` dla ProgramDriven. Raport jest drukowany wyłącznie po sprawdzeniu arytmetyki, dowodów `TRANSPORT_END`, specyfikacji min/max, flag naruszeń, duplikatów i wykluczenia ST23/ST24.


## Optymalizacja - etap 2: evaluator ProgramDriven

Dodano `ProgramCandidateEvaluator`, który dla każdego kandydata tworzy głęboką kopię konfiguracji, ustawia pozycje startowe M1-M4 i uruchamia istniejący program PLC wraz z consultami w ProgramDriven. Kandydat jest odrzucany przy deadlocku, naruszeniu procesu/residence, ostrzeżeniu przepływu materiału, konflikcie TrackGuard lub braku zamknięcia pozycji cyklu. Ranking uwzględnia cycle time, czas bezczynności nad wannami procesowymi, consult waits, TrackGuard waits, puste przejazdy i throughput. Ten etap nie regeneruje jeszcze programu PLC ani consultów dla każdej kandydatury.


## Optymalizacja - etap 3: ProgramCandidateTransformer

Dodano transformację kopii programów i consultów dla kandydata. Transformer ustawia CYCLE_START_HOLD, przekierowuje istniejące kroki parkingowe, może wstawić ruch CONSULT_PREPOSITION przed chronioną operacją, przelicza indeksy PLC i adresy MW consultów oraz dopisuje mierzony POWROT_CYKL. Transformacja odrzuca parking procesowy, jeżeli istnieje legalna pozycja nieprocesowa, przekroczenie limitu WORD, zablokowaną ścieżkę powrotu oraz powrót po końcowym PICKUP. ProgramCandidateEvaluator może opcjonalnie uruchamiać transformed program.


## Optymalizacja - etap 4: trajectory-aware consult preposition

Dodano `TrajectoryAwarePrepositionPlanner`, który korzysta z rzeczywiście zmierzonych okresów `consult_waits` oraz liniowej geometrii `ProgramTrackConflictDetector`. Planner wybiera najbliższe celowi nieprocesowe stanowisko osiągalne podczas aktywnego consultu, sprawdza cały ruch oraz postój do czasu zwolnienia consultu względem trajektorii pozostałych manipulatorów. Dodano dwuprzebiegowy `TrajectoryAwareOptimizationPipeline`: przebieg bazowy -> decyzje podejścia -> transformacja -> końcowy ProgramDriven. Transformer przyjmuje teraz osobną pozycję podejścia dla pary `(manipulator, source_plc_index)`.


## Optymalizacja - etap 5: batch study, cache i finaliści

Dodano `OptimizationStudy` z dwufazową selekcją kandydatów: screening i końcową walidacją finalistów. Studium obsługuje limit kandydatów, liczbę finalistów, callback postępu i bezpieczne anulowanie pomiędzy kandydatami. `OptimizationCache` zapisuje lekkie wyniki do JSONL pod hashem studium, fazy i parametrów kandydata, dzięki czemu badanie można wznowić bez powtarzania obliczonych wariantów. `OptimizationReport` eksportuje ranking do CSV UTF-8 oraz JSON. Ciężkie obiekty SimulationResult nie są serializowane w cache.


## Optymalizacja - Etapy 6 i 7

Zintegrowano zakładkę `Optymalizacja` z `MainWindow`, aktualnym programem PLC i consultami `CyclogramTab`. GUI uruchamia badanie w `QThread`, pokazuje screening/finał, ranking, cache i pozwala bezpiecznie przerwać pomiędzy kandydatami. `OptimizationStudyFactory` buduje pełne pipeline z bieżącego projektu oraz fingerprint cache. Etap 7 dodaje podgląd wariantu, obowiązkowe ponowne przeliczenie przed zastosowaniem, podmianę programu/consultów/pozycji startowych, aktualizację wyników i trajektorii oraz jednopoziomowe cofnięcie w pamięci.


## Hotfix v1.1.0a7.1 - mapowanie kolumn ProcessTab

Naprawiono regresję po dodaniu kolumny `Wanna procesowa`. `_load_data()` wpisywało `drip_time` do kolumny Max Time (5), a `shared_bath_group` do kolumny Czas ocieku (6), pozostawiając Shared Bath (7) pustą. Wprowadzono jawne stałe `COLUMN_*`, poprawiono odczyt i zapis wszystkich pól oraz normalizację pustego Shared Bath, aby wartość `None` nie była wyświetlana jako tekst.


## Hotfix v1.1.0a7.2 - imported consults i screening

Naprawiono zgodność `ImportedProgramConsult` z optymalizatorem (`reason=IMPORTED_TXT`) i bezpieczny fallback w fingerprint. Poprawiono mapowanie kluczy `ProgramCycleKPI`, przez co cycle time nie jest już `inf`. Generator studium umieszcza teraz bieżące, sprawdzone pozycje startowe M1-M4 przed siatką leksykograficzną, dzięki czemu limit 500 nie jest zużywany wyłącznie na warianty jednego skrajnego startu. Zmieniono schemat fingerprintu cache, aby stare odrzucone wyniki nie były ponownie używane.


## Hotfix v1.1.0a7.3 - audyt remapowania consultów

Transformer zapisuje sygnatury źródłowego i docelowego rozkazu każdego consultu przed modyfikacją programu, przelicza indeksy po wstawieniu kroków i potwierdza, że nowe indeksy nadal wskazują te same rozkazy. Niezgodność zatrzymuje kandydata kodem `CONSULT_SOURCE_REMAP_MISMATCH` lub `CONSULT_TARGET_REMAP_MISMATCH`. Pipeline oznacza teraz błędy fazą `BASELINE_` albo `TRANSFORMED_`. Błędy materiałowe obecne już w bazowym programie zatrzymują transformację, dzięki czemu tabela jednoznacznie pokazuje, czy problem występuje przed, czy po zmianie consultów.


## Etap 8.0 - kandydaci EventDriven i shared bath

Rozpoczęto nową strategię optymalizacji: parametry są nakładane na kopię konfiguracji przed EventDriven, a program PLC i consulty będą generowane później od zera. Dodano modele `EventDrivenCandidate` i `SharedBathCandidateParameter`, generator kombinacji trybów faktycznie obsługiwanych przez `SharedBathSelector` (`percent`, `seconds`, `alternate`), generator legalnych pozycji startowych oraz bezpieczny applier. Applier może zmieniać `shared_bath_stagger_mode` i `shared_bath_stagger_value`, ale kontroluje niezmienność min/max procesu, czasu ocieku, aktywności i przynależności do grupy shared bath.


## Etap 8.1 - EventDrivenCandidateEvaluator

Dodano evaluator screeningu kandydatów EventDriven. Każdy kandydat jest nakładany na głęboką kopię konfiguracji, uruchamia istniejący `EventDrivenSimulator`, a następnie zbiera KPI, steady state, compliance min/max, deadlocki, naruszenia procesu i wykorzystanie stanowisk shared bath na podstawie `TRANSPORT_END`. Wynik ma status VALID/REJECTED i powody `EVENT_*`. Evaluator nie generuje jeszcze programu PLC ani consultów.


## Etap 8.15 - Repeatable side-effect-free EventTrackYield

- YIELD ma dwa etapy: `propose()` bez zmiany stanu i `commit()` po wyborze.
- Pierwszy przebieg selektora ocenia zwykłe przydziały bez YIELD.
- Drugi przebieg uruchamia YIELD tylko, gdy nie istnieje legalny zwykły przydział.
- Blokada duplikatu wygasa po zakończeniu ruchu, więc ten sam sąsiad może ustąpić ponownie w kolejnym cyklu.
- `YieldTimelineIntegrator` rozcina nakładające segmenty idle i wstawia rzeczywistą pozycję po YIELD.
- Stabilne zero z deadlockiem lub transportami odroczonymi nie jest uznawane za prawidłowy steady state.
- Regresja: 214 testów PASS.
