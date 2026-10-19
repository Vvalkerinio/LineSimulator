from pathlib import Path
import pytest
from src.io.configuration_serializer import create_default_configuration
from src.model.station_numbering import STATION_ID_SHIFT, display_station_id, internal_station_id


def test_numbering_roundtrip_and_boundaries():
    assert STATION_ID_SHIFT == 1
    assert display_station_id(1) == 2
    assert display_station_id(22) == 23
    assert internal_station_id(2) == 1
    assert internal_station_id(23) == 22
    with pytest.raises(ValueError):
        internal_station_id(1)


def test_geometry_remains_internal_and_display_is_shifted():
    config = create_default_configuration()
    assert [s.id for s in config.stations] == list(range(1, 23))
    assert [display_station_id(s.id) for s in config.stations] == list(range(2, 24))
    assert min(m.work_zone_start for m in config.manipulators) == 1
    assert max(m.work_zone_end for m in config.manipulators) == 22


def test_cyclogram_has_fixed_hidden_shift_and_bidirectional_conversion():
    source = Path('src/gui/cyclogram_tab.py').read_text(encoding='utf-8')
    assert '"Shift ID stanowiska"' not in source
    assert 'self.station_id_shift.hide()' in source
    assert 'STATION_ID_SHIFT' in source
    assert 'internal_station_id(displayed_station_id)' in source
    assert 'str(display_station_id(step.station_id))' in source


def test_process_animation_and_reports_use_display_ids():
    process = Path('src/gui/process_tab.py').read_text(encoding='utf-8')
    animation = Path('src/gui/station_animation_widget.py').read_text(encoding='utf-8')
    compliance = Path('src/analysis/process_compliance_report.py').read_text(encoding='utf-8')
    assert 'display_station_id(station.id)' in process
    assert 'display_station_id(station_id)' in animation
    assert 'display_station_id(r.station_id)' in compliance
