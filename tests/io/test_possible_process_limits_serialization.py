from src.io.configuration_serializer import _station_from_dict, _station_to_dict

def test_old_station_json_defaults_possible_limits_to_nominal():
    station = _station_from_dict({
        "id": 2, "name": "Bath", "enabled": True,
        "min_process_time": 230, "max_process_time": 300
    })
    assert station.possible_min_process_time == 230
    assert station.possible_max_process_time == 300

def test_new_station_json_roundtrips_possible_limits():
    station = _station_from_dict({
        "id": 2, "name": "Bath", "enabled": True,
        "min_process_time": 230, "max_process_time": 300,
        "possible_min_process_time": 210,
        "possible_max_process_time": 330
    })
    data = _station_to_dict(station)
    assert data["possible_min_process_time"] == 210
    assert data["possible_max_process_time"] == 330
