"""照片新增模式: 新照片資料夾放在硬碟資料夾裡面時,掃描硬碟要跳過它"""
import os

from src.core.cache import CacheManager
from src.core.scanner import FileScanner, DeduplicateFinder


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return str(path)


def _scanner(tmp_path):
    return FileScanner(CacheManager(str(tmp_path / "cache.db")))


def _make_nested_layout(tmp_path):
    """
    目標/
    ├── 舊照片A.jpg          (內容 A)
    └── 新匯入/
        ├── IMG_1.jpg        (內容 A,真的重複)
        └── IMG_2.jpg        (內容 B,全新)
    """
    disk = tmp_path / "目標"
    new = disk / "新匯入"
    old_a = _write(disk / "舊照片A.jpg", b"content-A")
    img_1 = _write(new / "IMG_1.jpg", b"content-A")
    img_2 = _write(new / "IMG_2.jpg", b"content-B")
    return str(disk), str(new), old_a, img_1, img_2


def test_disk_scan_skips_excluded_new_folder(tmp_path):
    disk, new, old_a, img_1, img_2 = _make_nested_layout(tmp_path)

    disk_files = _scanner(tmp_path).scan_folders([disk], exclude_folders=[new])

    assert set(disk_files) == {old_a}


def test_nested_new_folder_only_true_duplicates_are_found(tmp_path):
    disk, new, old_a, img_1, img_2 = _make_nested_layout(tmp_path)
    scanner = _scanner(tmp_path)

    new_files = scanner.scan_folders([new])
    disk_files = scanner.scan_folders([disk], exclude_folders=[new])
    duplicates = DeduplicateFinder.find_new_duplicates(new_files, disk_files)

    assert duplicates == [img_1]


def test_exclude_matches_same_folder_through_symlink(tmp_path):
    disk, new, old_a, img_1, img_2 = _make_nested_layout(tmp_path)
    link = tmp_path / "捷徑"
    os.symlink(new, link)

    disk_files = _scanner(tmp_path).scan_folders([disk], exclude_folders=[str(link)])

    assert set(disk_files) == {old_a}


def test_scan_without_exclude_includes_subfolders(tmp_path):
    disk, new, old_a, img_1, img_2 = _make_nested_layout(tmp_path)

    disk_files = _scanner(tmp_path).scan_folders([disk])

    assert set(disk_files) == {old_a, img_1, img_2}
