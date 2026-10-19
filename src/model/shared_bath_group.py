from dataclasses import dataclass


@dataclass
class SharedBathGroup:

    group_id: str

    station_ids: list[int]