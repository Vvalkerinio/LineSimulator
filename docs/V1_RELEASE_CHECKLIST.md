# Checklista wydania v1.0

- [ ] Czyste środowisko instaluje `requirements.txt`.
- [ ] `python -m compileall -q src tests` przechodzi.
- [ ] `python -m pytest -q` przechodzi bez FAIL/ERROR.
- [ ] Aplikacja startuje przez `py -m src.gui.app`.
- [ ] Konfiguracja zapisuje i odczytuje drip time, MW Index, offsety i TrackGuard.
- [ ] EventDriven kończy symulację bez deadlocka.
- [ ] Program PLC generuje jawny krok startowy.
- [ ] Import PLC używa adresów MW Index z GUI.
- [ ] Eksport PLC zawiera wyłącznie komendy.
- [ ] Consulty można generować, edytować, importować i eksportować.
- [ ] ProgramDriven obsługuje ST23/ST24.
- [ ] TrackGuard OFF/WARN/ENFORCE ma zgodne zachowanie.
- [ ] Ociek po PODNIES odpowiada konfiguracji stanowiska.
- [ ] Throughput = hanger exits / pełny czas cykli.
- [ ] Station residence nie zawiera drip time.
- [ ] Trajektorie pokazują indeksy PLC i pomiar A/B.
- [ ] Brak plików cache, backupów i patcherów w paczce wydania.
