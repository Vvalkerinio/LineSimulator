from dataclasses import dataclass


@dataclass
class StationState:

    station_id: int

    occupied: bool = False

    hanger_id: int | None = None

    #
    # Czas zakończenia procesu technologicznego.
    #
    # UWAGA:
    # To NIE oznacza zwolnienia stanowiska.
    # Stanowisko jest fizycznie zajęte dopóki
    # hanger_id nie zostanie wyczyszczony przez release().
    #
    occupied_until: float = 0.0