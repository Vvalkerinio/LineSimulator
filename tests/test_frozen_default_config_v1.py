from pathlib import Path
from types import SimpleNamespace

from src.io import configuration_serializer


def test_bundled_default_path_uses_pyinstaller_meipass(monkeypatch):
    monkeypatch.setattr(
        configuration_serializer.sys,
        "_MEIPASS",
        str(Path("bundle-root")),
        raising=False
    )
    assert configuration_serializer._bundled_default_config_path() == (
        Path("bundle-root") / "configs" / "default.json"
    )


def test_bundled_default_path_is_none_outside_frozen_app(monkeypatch):
    monkeypatch.delattr(
        configuration_serializer.sys,
        "_MEIPASS",
        raising=False
    )
    assert configuration_serializer._bundled_default_config_path() is None
