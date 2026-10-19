from pathlib import Path
s=Path('src/gui/cyclogram_tab.py').read_text(encoding='utf-8')

def test_selection_helper_present():
    assert '_select_table_row' in s
    assert 'self._select_table_row(self.table' in s
    assert 'self._select_table_row(self.consult_table' in s

def test_default_folders_present():
    assert 'examples" / "plc' in s
    assert 'examples" / "consults' in s
