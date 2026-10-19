from dataclasses import dataclass


@dataclass
class BathGroup:

    id: str

    name: str

    stations: list[int]