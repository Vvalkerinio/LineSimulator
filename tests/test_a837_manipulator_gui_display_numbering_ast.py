from pathlib import Path


def test_all_user_visible_manipulator_positions_use_display_numbering():
    source = Path('src/gui/manipulator_tab.py').read_text(encoding='utf-8')
    assert '"Pozycja startowa [ST]"' in source
    assert '"Ulubiony parking [ST]"' in source
    assert '"Strefa od [ST]"' in source
    assert '"Strefa do [ST]"' in source
    assert source.count('display_station_id(') >= 4
    assert source.count('internal_station_id(') >= 4
    assert 'position = internal_station_id(' in source
    assert 'zone_start = internal_station_id(' in source
    assert 'zone_end = internal_station_id(' in source


def test_visible_station_spinboxes_are_limited_to_2_23():
    source = Path('src/gui/manipulator_tab.py').read_text(encoding='utf-8')
    assert source.count('                    2,\n                    23') >= 4


def test_gui_rejects_colliding_start_positions_before_model_update():
    source = Path('src/gui/manipulator_tab.py').read_text(encoding='utf-8')
    assert '"Kolizja pozycji startowych"' in source
    assert 'minimum_manipulator_spacing' in source
    assert 'proposed = []' in source
    assert 'for item in proposed:' in source
