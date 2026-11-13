import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path_factory, monkeypatch):
    """把 HOME 導到暫存資料夾,確保測試不會寫到真正的 ~/Desktop 或 ~/.photo_dedup_cache.db"""
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
    return home
