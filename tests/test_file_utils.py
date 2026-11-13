"""file_utils 測試"""
import os
from pathlib import Path

from src.utils.file_utils import (
    check_add_new_folders,
    get_mirrored_dest_path,
    get_unique_path,
)

REMOVED_TEMPLATE = "待移除項目_{date}"


# === check_add_new_folders (照片新增模式: 新照片資料夾 vs 硬碟資料夾) ===


def _mkdir(path):
    os.makedirs(path)
    return str(path)


def test_new_folder_same_as_disk_folder_is_rejected(tmp_path):
    disk = _mkdir(tmp_path / "照片")

    is_valid, _ = check_add_new_folders(disk, [disk])

    assert not is_valid


def test_new_folder_inside_disk_folder_is_accepted(tmp_path):
    disk = _mkdir(tmp_path / "照片")
    new = _mkdir(tmp_path / "照片" / "2026新匯入")

    is_valid, error_msg = check_add_new_folders(new, [disk])

    assert is_valid
    assert error_msg == ""


def test_disk_folder_inside_new_folder_is_rejected(tmp_path):
    new = _mkdir(tmp_path / "匯入")
    disk = _mkdir(tmp_path / "匯入" / "已整理")

    is_valid, _ = check_add_new_folders(new, [disk])

    assert not is_valid


def test_new_folder_symlinked_to_disk_folder_is_rejected(tmp_path):
    disk = _mkdir(tmp_path / "照片")
    new = tmp_path / "捷徑"
    os.symlink(disk, new)

    is_valid, _ = check_add_new_folders(str(new), [disk])

    assert not is_valid


def test_disk_folder_inside_new_folder_among_several_is_rejected(tmp_path):
    new = _mkdir(tmp_path / "匯入")
    disk_a = _mkdir(tmp_path / "A")
    disk_b = _mkdir(tmp_path / "匯入" / "B")

    is_valid, _ = check_add_new_folders(new, [disk_a, disk_b])

    assert not is_valid


def test_nested_disk_folders_are_rejected(tmp_path):
    disk_a = _mkdir(tmp_path / "A")
    disk_b = _mkdir(tmp_path / "A" / "B")
    new = _mkdir(tmp_path / "新照片")

    is_valid, _ = check_add_new_folders(new, [disk_a, disk_b])

    assert not is_valid


def test_separate_folders_are_accepted(tmp_path):
    disk = _mkdir(tmp_path / "照片")
    new = _mkdir(tmp_path / "新照片")

    is_valid, error_msg = check_add_new_folders(new, [disk])

    assert is_valid
    assert error_msg == ""


def test_similar_name_prefix_is_not_treated_as_overlap(tmp_path):
    new = _mkdir(tmp_path / "photos")
    disk = _mkdir(tmp_path / "photos2")

    is_valid, _ = check_add_new_folders(new, [disk])

    assert is_valid


# === get_mirrored_dest_path (移到輸出資料夾時保留原本的資料夾結構) ===

def test_mirrored_dest_path_on_volume_keeps_structure_under_volume_root():
    dest = get_mirrored_dest_path(
        "/Volumes/測試硬碟_不存在/照片/2026/IMG_0001.jpg", REMOVED_TEMPLATE
    )

    parts = Path(dest).parts
    assert parts[:3] == ("/", "Volumes", "測試硬碟_不存在")
    assert parts[3].startswith("待移除項目_")
    assert parts[4:] == ("照片", "2026", "IMG_0001.jpg")


def test_mirrored_dest_path_on_local_disk_keeps_full_path_under_desktop(tmp_path):
    source = tmp_path / "照片" / "IMG_0001.jpg"

    dest = Path(get_mirrored_dest_path(str(source), REMOVED_TEMPLATE))

    desktop = Path(os.path.expanduser("~/Desktop"))
    assert dest.parent.parent != desktop  # 不是攤平成單一檔名
    assert dest.relative_to(desktop).parts[0].startswith("待移除項目_")
    assert dest.parts[-len(source.resolve().parts) + 1:] == source.resolve().parts[1:]


def test_paths_that_used_to_flatten_to_same_name_get_different_dests(tmp_path):
    a = tmp_path / "a_b" / "c.jpg"
    b = tmp_path / "a" / "b_c.jpg"

    assert get_mirrored_dest_path(str(a), REMOVED_TEMPLATE) != \
        get_mirrored_dest_path(str(b), REMOVED_TEMPLATE)


# === get_unique_path (目的地已有檔案時自動改名) ===

def test_unique_path_returns_same_path_when_free(tmp_path):
    path = str(tmp_path / "IMG_0001.jpg")

    assert get_unique_path(path) == path


def test_unique_path_adds_suffix_when_taken(tmp_path):
    (tmp_path / "IMG_0001.jpg").write_bytes(b"x")

    assert get_unique_path(str(tmp_path / "IMG_0001.jpg")) == str(tmp_path / "IMG_0001_1.jpg")


def test_unique_path_skips_suffixes_already_taken(tmp_path):
    (tmp_path / "IMG_0001.jpg").write_bytes(b"x")
    (tmp_path / "IMG_0001_1.jpg").write_bytes(b"x")

    assert get_unique_path(str(tmp_path / "IMG_0001.jpg")) == str(tmp_path / "IMG_0001_2.jpg")
