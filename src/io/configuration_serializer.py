import sys

import json

from pathlib import Path

from src.model.station import (
    Station
)
from src.model.manipulator import (
    Manipulator
)
from src.model.simulation_configuration import (
    SimulationConfiguration
)
from src.model.start_mode import (
    StartMode
)

try:
    from src.model.shared_bath_group import (
        SharedBathGroup
    )
except ImportError:
    SharedBathGroup = None


CONFIG_DIR = Path(
    "configs"
)

DEFAULT_CONFIG_PATH = (
    CONFIG_DIR
    / "default.json"
)


def _bundled_default_config_path():
    """Return the read-only config bundled by PyInstaller, when available."""
    bundle_root = getattr(
        sys,
        "_MEIPASS",
        None
    )
    if bundle_root is None:
        return None
    return (
        Path(bundle_root)
        / "configs"
        / "default.json"
    )


def create_default_configuration():
    stations = [
        Station(
            i,
            f"P{i}",
            True,
            10,
            300
        )
        for i in range(
            1,
            23
        )
    ]
    for station in stations:
        station.is_process_bath = station.id not in (1, 22, 23, 24)

    manipulators = [
        Manipulator(
            id=1,
            position=1,
            lift_time=3,
            drop_time=3,
            travel_time_per_position=2,
            work_zone_start=1,
            work_zone_end=8
        ),
        Manipulator(
            id=2,
            position=8,
            lift_time=3,
            drop_time=3,
            travel_time_per_position=2,
            work_zone_start=8,
            work_zone_end=19
        ),
        Manipulator(
            id=3,
            position=19,
            lift_time=3,
            drop_time=3,
            travel_time_per_position=2,
            work_zone_start=19,
            work_zone_end=21
        ),
        Manipulator(
            id=4,
            position=21,
            lift_time=3,
            drop_time=3,
            travel_time_per_position=2,
            work_zone_start=21,
            work_zone_end=22
        )
    ]

    from src.core.shared_bath_group_builder import (
        SharedBathGroupBuilder
    )

    shared_bath_groups = (
        SharedBathGroupBuilder()
        .build(
            stations
        )
    )

    return SimulationConfiguration(
        stations=(
            stations
        ),
        manipulators=(
            manipulators
        ),
        shared_bath_groups=(
            shared_bath_groups
        ),
        start_mode=(
            StartMode.EMPTY
        ),
        minimum_manipulator_spacing=(
            2.0
        )
    )


def _station_to_dict(
    station
):
    return {
        "id":
            station.id,

        "name":
            station.name,

        "enabled":
            station.enabled,

        "min_process_time":
            station.min_process_time,

        "max_process_time":
            station.max_process_time,

        "possible_min_process_time":
            getattr(station, "possible_min_process_time", station.min_process_time),

        "possible_max_process_time":
            getattr(station, "possible_max_process_time", station.max_process_time),

        "drip_time":
            getattr(station, "drip_time", 0.0),

        "is_process_bath":
            bool(getattr(station, "is_process_bath", True)),

        "shared_bath_group":
            getattr(
                station,
                "shared_bath_group",
                None
            ),

        "shared_bath_stagger_mode":
            getattr(
                station,
                "shared_bath_stagger_mode",
                "percent"
            ),

        "shared_bath_stagger_value":
            getattr(
                station,
                "shared_bath_stagger_value",
                50.0
            )
    }

def _station_from_dict(
    data
):
    station = Station(
        id=(
            int(
                data[
                    "id"
                ]
            )
        ),

        name=(
            data.get(
                "name",
                f"P{data['id']}"
            )
        ),

        enabled=(
            bool(
                data.get(
                    "enabled",
                    True
                )
            )
        ),

        min_process_time=(
            float(
                data.get(
                    "min_process_time",
                    10.0
                )
            )
        ),

        max_process_time=(
            float(
                data.get(
                    "max_process_time",
                    300.0
                )
            )
        ),

        possible_min_process_time=(
            float(data.get(
                "possible_min_process_time",
                data.get("min_process_time", 10.0)
            ))
        ),

        possible_max_process_time=(
            float(data.get(
                "possible_max_process_time",
                data.get("max_process_time", 300.0)
            ))
        ),

        drip_time=(
            float(data.get("drip_time", 0.0))
        ),

        is_process_bath=(
            bool(data.get(
                "is_process_bath",
                int(data.get("id", 0)) not in (1, 22, 23, 24)
            ))
        ),

        shared_bath_group=(
            data.get(
                "shared_bath_group",
                None
            )
        )
    )

    station.shared_bath_stagger_mode = (
        data.get(
            "shared_bath_stagger_mode",
            "percent"
        )
    )

    station.shared_bath_stagger_value = (
        float(
            data.get(
                "shared_bath_stagger_value",
                50.0
            )
        )
    )

    return station

def _manipulator_to_dict(
    manipulator
):
    return {
        "id":
            manipulator.id,
        "position":
            manipulator.position,
        "lift_time":
            manipulator.lift_time,
        "drop_time":
            manipulator.drop_time,
        "travel_time_per_position":
            manipulator.travel_time_per_position,
        "work_zone_start":
            getattr(
                manipulator,
                "work_zone_start",
                1
            ),
        "work_zone_end":
            getattr(
                manipulator,
                "work_zone_end",
                999
            ),
        "preferred_parking_position":
            getattr(
                manipulator,
                "preferred_parking_position",
                manipulator.position
            )
    }


def _manipulator_from_dict(
    data
):
    return Manipulator(
        id=(
            int(
                data[
                    "id"
                ]
            )
        ),
        position=(
            int(
                data.get(
                    "position",
                    1
                )
            )
        ),
        lift_time=(
            float(
                data.get(
                    "lift_time",
                    3.0
                )
            )
        ),
        drop_time=(
            float(
                data.get(
                    "drop_time",
                    3.0
                )
            )
        ),
        travel_time_per_position=(
            float(
                data.get(
                    "travel_time_per_position",
                    2.0
                )
            )
        ),
        work_zone_start=(
            int(
                data.get(
                    "work_zone_start",
                    1
                )
            )
        ),
        work_zone_end=(
            int(
                data.get(
                    "work_zone_end",
                    999
                )
            )
        ),
        preferred_parking_position=(
            int(data.get(
                "preferred_parking_position",
                data.get("position", 1)
            ))
        )
    )


def _shared_bath_group_to_dict(
    group
):
    return {
        "group_id":
            group.group_id,
        "station_ids":
            list(
                group.station_ids
            )
    }


def _shared_bath_group_from_dict(
    data
):
    if SharedBathGroup is None:
        return data

    return SharedBathGroup(
        group_id=(
            data[
                "group_id"
            ]
        ),
        station_ids=[
            int(
                value
            )
            for value
            in data.get(
                "station_ids",
                []
            )
        ]
    )


def configuration_to_dict(
    configuration
):
    start_mode = (
        StartMode.from_value(
            getattr(
                configuration,
                "start_mode",
                StartMode.EMPTY
            )
        )
    )

    return {
        "version":
            "14.0.0",
        "stations": [
            _station_to_dict(
                station
            )
            for station
            in configuration.stations
        ],
        "manipulators": [
            _manipulator_to_dict(
                manipulator
            )
            for manipulator
            in configuration.manipulators
        ],
        "hanger_count":
            configuration.hanger_count,
        "entry_interval":
            configuration.entry_interval,
        "pieces_per_transport":
            int(getattr(configuration, "pieces_per_transport", 7)),
        "infinite_feed":
            getattr(
                configuration,
                "infinite_feed",
                False
            ),
        "feed_duration":
            getattr(
                configuration,
                "feed_duration",
                3600.0
            ),
        "warmup_time":
            getattr(
                configuration,
                "warmup_time",
                1800.0
            ),
        "steady_state_window":
            getattr(
                configuration,
                "steady_state_window",
                300.0
            ),
        "start_mode":
            start_mode.value,
        "minimum_manipulator_spacing":
            getattr(
                configuration,
                "minimum_manipulator_spacing",
                2.0
            ),
        "program_index_addresses":
            {
                str(key): int(value)
                for key, value in getattr(
                    configuration,
                    "program_index_addresses",
                    {1: 500, 2: 600, 3: 700, 4: 800}
                ).items()
            },
        "program_station_offsets":
            {
                str(key): int(value)
                for key, value in getattr(
                    configuration,
                    "program_station_offsets",
                    {1: 0, 2: 0, 3: 0, 4: 0}
                ).items()
            },
        "program_driven_transfer_enabled":
            getattr(configuration, "program_driven_transfer_enabled", True),
        "program_driven_transfer_drop_23_delay":
            getattr(configuration, "program_driven_transfer_drop_23_delay", 0.5),
        "program_driven_transfer_pickup_24_delay":
            getattr(configuration, "program_driven_transfer_pickup_24_delay", 0.5),
        "program_driven_unload_drop_22_delay":
            getattr(configuration, "program_driven_unload_drop_22_delay", 0.5),
        "shared_bath_groups": [
            _shared_bath_group_to_dict(
                group
            )
            for group
            in getattr(
                configuration,
                "shared_bath_groups",
                []
            )
        ],

        
    }


def configuration_from_dict(
    data
):
    stations = [
        _station_from_dict(
            item
        )
        for item
        in data.get(
            "stations",
            []
        )
    ]

    manipulators = [
        _manipulator_from_dict(
            item
        )
        for item
        in data.get(
            "manipulators",
            []
        )
    ]

    shared_bath_groups = [
        _shared_bath_group_from_dict(
            item
        )
        for item
        in data.get(
            "shared_bath_groups",
            []
        )
    ]
    
    configuration = SimulationConfiguration(
        stations=(
            stations
        ),
        manipulators=(
            manipulators
        ),
        hanger_count=(
            int(
                data.get(
                    "hanger_count",
                    1
                )
            )
        ),
        entry_interval=(
            float(
                data.get(
                    "entry_interval",
                    60.0
                )
            )
        ),
        pieces_per_transport=max(
            1,
            int(data.get("pieces_per_transport", 7))
        ),
        infinite_feed=(
            bool(
                data.get(
                    "infinite_feed",
                    False
                )
            )
        ),
        feed_duration=(
            float(
                data.get(
                    "feed_duration",
                    data.get(
                        "simulation_duration",
                        3600.0
                    )
                )
            )
        ),
        warmup_time=(
            float(
                data.get(
                    "warmup_time",
                    1800.0
                )
            )
        ),
        steady_state_window=(
            float(
                data.get(
                    "steady_state_window",
                    300.0
                )
            )
        ),
        start_mode=(
            StartMode.from_value(
                data.get(
                    "start_mode",
                    StartMode.EMPTY
                )
            )
        ),
        minimum_manipulator_spacing=(
            float(
                data.get(
                    "minimum_manipulator_spacing",
                    2.0
                )
            )
        ),
        shared_bath_groups=(
            shared_bath_groups
        )
    )
    configuration.program_index_addresses = {
        int(key): int(value)
        for key, value in data.get(
            "program_index_addresses",
            {"1": 500, "2": 600, "3": 700, "4": 800}
        ).items()
    }
    configuration.program_station_offsets = {
        int(key): int(value)
        for key, value in data.get(
            "program_station_offsets",
            {"1": 0, "2": 0, "3": 0, "4": 0}
        ).items()
    }
    configuration.program_driven_transfer_enabled = bool(
        data.get("program_driven_transfer_enabled", True)
    )
    configuration.program_driven_transfer_drop_23_delay = float(
        data.get("program_driven_transfer_drop_23_delay", 0.5)
    )
    configuration.program_driven_transfer_pickup_24_delay = float(
        data.get("program_driven_transfer_pickup_24_delay", 0.5)
    )
    configuration.program_driven_unload_drop_22_delay = float(
        data.get("program_driven_unload_drop_22_delay", 0.5)
    )
    return configuration
    
    

def save_configuration(
    configuration,
    path
):
    path = Path(
        path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    data = (
        configuration_to_dict(
            configuration
        )
    )

    with path.open(
        "w",
        encoding="utf-8"
    ) as handle:
        json.dump(
            data,
            handle,
            indent=4,
            ensure_ascii=False
        )


def load_configuration(
    path
):
    path = Path(
        path
    )

    with path.open(
        "r",
        encoding="utf-8"
    ) as handle:
        data = (
            json.load(
                handle
            )
        )

    return configuration_from_dict(
        data
    )


def save_default_configuration(
    configuration
):
    save_configuration(
        configuration,
        DEFAULT_CONFIG_PATH
    )


def load_default_configuration():
    if DEFAULT_CONFIG_PATH.exists():
        return load_configuration(
            DEFAULT_CONFIG_PATH
        )

    bundled_path = _bundled_default_config_path()
    if (
        bundled_path is not None
        and bundled_path.exists()
    ):
        return load_configuration(
            bundled_path
        )

    return create_default_configuration()