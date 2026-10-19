# RELEASE NOTES 1.1.0a8.45

## Kompleksowa ochrona stanu początkowego
- Dodano centralny SimulationPreflightValidator używany przez EventDriven i ProgramDriven.
- Symulacja nie rozpocznie się z kolizją t=0, odwróconą kolejnością manipulatorów, pozycją poza strefą lub parkingiem poza strefą.
- Walidowane są unikalne identyfikatory manipulatorów i stanowisk oraz geometria stanowisk 1..22.
- Walidowana jest relacja Possible Min <= Min <= Max <= Possible Max.

## Izolacja konfiguracji runtime
- EventDriven w GUI pozostaje uruchamiany na deepcopy konfiguracji edytora.
- ProgramDriven w Cyklogramie również otrzymuje deepcopy konfiguracji.
- Pozycje końcowe żadnego silnika nie modyfikują pozycji startowych kolejnego uruchomienia.

## Testy
- Dodano testy poprawnego i kolizyjnego startu, stref, parkingów i limitów procesu.
- Dodano test AST izolacji obu GUI simulatorów.
- Skorygowano dwa historyczne testy return-after-drop do faktycznej semantyki: transport kończy się na DROP.
