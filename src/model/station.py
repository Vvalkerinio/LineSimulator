from dataclasses import dataclass


@dataclass
class Station:
    id: int
    name: str
    enabled: bool
    min_process_time: float
    max_process_time: float
    shared_bath_group: str | None = None
    drip_time: float = 0.0
    is_process_bath: bool = True
    possible_min_process_time: float | None = None
    possible_max_process_time: float | None = None

    def __post_init__(self):
        if self.possible_min_process_time is None:
            self.possible_min_process_time = float(self.min_process_time)
        if self.possible_max_process_time is None:
            self.possible_max_process_time = float(self.max_process_time)
