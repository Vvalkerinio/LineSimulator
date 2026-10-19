from src.core.shared_bath_selector import (
    SharedBathSelector
)


class EmptyStationManager:

    def is_available(self, station_id, current_time):
        return True


def test_selects_first_station_when_candidates_are_equivalent():
    selector = SharedBathSelector(
        EmptyStationManager()
    )

    selected = selector.select(
        [9, 10],
        0
    )

    assert selected == 9
    assert selector.last_recommended_time == 0.0
