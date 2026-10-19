from src.model.station import (
    Station
)

from src.gui.station_table_model import (
    StationTableModel
)


def test_station_update():

    station = Station(
        id=1,
        name="P1",
        enabled=True,
        min_process_time=10,
        max_process_time=100
    )

    model = StationTableModel(
        [station]
    )

    model.update_station(
        row=0,
        name="KTL_TEST",
        enabled=False,
        min_time=20,
        max_time=200,
        shared_bath="KTL_1"
    )

    assert (
        station.name
        == "KTL_TEST"
    )

    assert (
        station.enabled
        is False
    )

    assert (
        station.min_process_time
        == 20
    )