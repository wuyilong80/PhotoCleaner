"""移動到待移除項目資料夾時,任何情況都不能覆蓋已經移過去的檔案"""
import os

import pytest

from src.core.cache import CacheManager
from src.core.file_operations import FileOperationManager


@pytest.fixture
def removed_dir(tmp_path, monkeypatch):
    """把輸出資料夾導到 tmp_path,避免寫到真正的桌面"""
    out = tmp_path / "removed"
    monkeypatch.setattr(
        "src.utils.file_utils.get_output_folder_path",
        lambda source, template: str(out),
    )
    return out


@pytest.fixture
def manager(tmp_path):
    return FileOperationManager(CacheManager(str(tmp_path / "cache.db")))


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return str(path)


def _contents_under(root):
    contents = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            with open(os.path.join(dirpath, name), "rb") as f:
                contents.append(f.read())
    return sorted(contents)


def test_files_whose_old_flattened_names_collide_are_both_kept(tmp_path, removed_dir, manager):
    a = _write(tmp_path / "src" / "a_b" / "c.jpg", b"photo-1")
    b = _write(tmp_path / "src" / "a" / "b_c.jpg", b"photo-2")

    ok, failed = manager.move_files_to_removed([a, b])

    assert (ok, failed) == (2, [])
    assert _contents_under(removed_dir) == [b"photo-1", b"photo-2"]


def test_moving_same_path_twice_keeps_both(tmp_path, removed_dir, manager):
    path = tmp_path / "src" / "IMG_0001.jpg"
    _write(path, b"first")
    manager.move_files_to_removed([str(path)])
    _write(path, b"second")

    ok, failed = manager.move_files_to_removed([str(path)])

    assert (ok, failed) == (1, [])
    assert _contents_under(removed_dir) == [b"first", b"second"]


def test_resume_pending_moves_does_not_overwrite_existing_dest(tmp_path, manager):
    source = _write(tmp_path / "src" / "IMG_0001.jpg", b"pending")
    dest = _write(tmp_path / "removed" / "IMG_0001.jpg", b"already-there")
    manager.cache_manager.save_pending_moves([(source, dest)])

    ok, failed = manager.resume_pending_moves()

    assert (ok, failed) == (1, [])
    assert _contents_under(tmp_path / "removed") == [b"already-there", b"pending"]


def test_corrupted_file_move_does_not_overwrite(tmp_path, removed_dir, manager):
    path = tmp_path / "src" / "broken.jpg"
    _write(path, b"broken-1")
    manager.move_corrupted_file(str(path))
    _write(path, b"broken-2")

    manager.move_corrupted_file(str(path))

    assert _contents_under(removed_dir) == [b"broken-1", b"broken-2"]
