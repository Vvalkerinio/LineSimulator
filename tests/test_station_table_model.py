from src.model.station import (
    Station
)

from src.gui.station_table_model import (
    StationTableModel
)


def test_station_model():

    model = StationTableModel(
        [
            Station(
                id=1,
                name="P1",
                enabled=True,
                min_process_time=10,
                max_process_time=100
            )
        ]
    )

    assert model.row_count() == 1

    assert (
        model.station(0).name
        == "P1"
    )