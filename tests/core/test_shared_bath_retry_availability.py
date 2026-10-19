from types import SimpleNamespace
from src.core.shared_bath_selector import SharedBathSelector

class StationManager:
    def __init__(self):
        self.items={3:SimpleNamespace(id=3,shared_bath_group="ODT",min_process_time=230),4:SimpleNamespace(id=4,shared_bath_group="ODT",min_process_time=230)}
    def station(self, station_id): return self.items[station_id]
    def state(self, station_id): return None

class Reservations:
    def __init__(self, values): self.values=values
    def earliest_available_time(self, station_id, current_time): return self.values[station_id]

def test_earliest_group_availability_returns_first_future_bath():
    selector=SharedBathSelector(StationManager(),Reservations({3:150.0,4:210.0}))
    assert selector.earliest_group_availability([3,4],100.0) == 150.0

def test_available_bath_keeps_rule_driven_recommendation():
    selector=SharedBathSelector(StationManager(),Reservations({3:100.0,4:210.0}))
    assert selector.earliest_group_availability([3,4],100.0) is None

def test_unknown_release_uses_no_group_override():
    selector=SharedBathSelector(StationManager(),Reservations({3:float("inf"),4:float("inf")}))
    assert selector.earliest_group_availability([3,4],100.0) is None
