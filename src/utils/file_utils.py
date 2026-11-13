"""檔案處理工具函數"""
import os
from pathlib import Path
from datetime import datetime
from .constants import SUPPORTED_EXTENSIONS


def is_supported_file(file_path):
    """檢查檔案是否為支援的格式"""
    ext = Path(file_path).suffix.lower()
    return ext in SUPPORTED_EXTENSIONS


def should_skip_file(file_path):
    """判斷是否應該跳過此檔案"""
    path = Path(file_path)

    # 隱藏檔案
    if path.name.startswith('.'):
        return True

    # 符號連結
    if path.is_symlink():
        return True

    return False


def should_skip_directory(dir_path):
    """判斷是否應該跳過此資料夾"""
    path = Path(dir_path)

    # 隱藏資料夾
    if path.name.startswith('.'):
        return True

    # 符號連結
    if path.is_symlink():
        return True

    return False


def is_nested_path(path1, path2):
    """檢查兩個路徑是否有巢狀關係"""
    try:
        p1 = Path(path1).resolve()
        p2 = Path(path2).resolve()

        # 檢查 p1 是否在 p2 內,或 p2 是否在 p1 內
        try:
            p1.relative_to(p2)
            return True
        except ValueError:
            pass

        try:
            p2.relative_to(p1)
            return True
        except ValueError:
            pass

        return False
    except Exception:
        return False


def get_output_folder_path(source_path, folder_template):
    """根據來源路徑決定輸出資料夾位置

    Args:
        source_path: 來源檔案路徑
        folder_template: 資料夾名稱模板 (例如: "待移除項目_{date}")

    Returns:
        輸出資料夾的完整路徑
    """
    date_str = datetime.now().strftime("%Y%m%d")
    folder_name = folder_template.format(date=date_str)

    source_path = Path(source_path).resolve()

    # 檢查是否為外接裝置 (/Volumes/ 開頭)
    if str(source_path).startswith('/Volumes/'):
        # 取得裝置名稱 (例如: /Volumes/HDD/... -> HDD)
        parts = source_path.parts
        if len(parts) >= 3:
            volume_name = parts[2]
            return f'/Volumes/{volume_name}/{folder_name}'

    # 本機路徑,放到桌面
    return os.path.expanduser(f'~/Desktop/{folder_name}')


def get_mirrored_dest_path(source_path, folder_template):
    """決定檔案移到輸出資料夾後的路徑,在輸出資料夾裡保留原本的資料夾結構

    外接裝置保留裝置內的路徑,本機檔案保留完整路徑。例如:
        /Volumes/HDD/旅遊/IMG_0001.jpg
            -> /Volumes/HDD/待移除項目_20261113/旅遊/IMG_0001.jpg
        /Users/me/Pictures/IMG_0001.jpg
            -> ~/Desktop/待移除項目_20261113/Users/me/Pictures/IMG_0001.jpg

    Args:
        source_path: 來源檔案路徑
        folder_template: 資料夾名稱模板 (例如: "待移除項目_{date}")

    Returns:
        目的地檔案的完整路徑
    """
    source = Path(source_path).resolve()
    output_folder = Path(get_output_folder_path(source, folder_template))

    parts = source.parts
    if str(source).startswith('/Volumes/') and len(parts) >= 3:
        # 去掉 /Volumes/<裝置名稱>
        relative = Path(*parts[3:])
    else:
        # 去掉開頭的 /
        relative = Path(*parts[1:])

    return str(output_folder / relative)


def get_unique_path(path):
    """若路徑已被佔用,在檔名後加上 _1、_2... 直到不重複

    例如: IMG_0001.jpg 已存在 -> IMG_0001_1.jpg
    """
    if not os.path.lexists(path):
        return path

    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.lexists(f"{base}_{counter}{ext}"):
        counter += 1
    return f"{base}_{counter}{ext}"


def check_folders_validity(folders, exclude_folders=None):
    """檢查資料夾清單的有效性

    Args:
        folders: 要檢查的資料夾清單
        exclude_folders: 要排除的資料夾清單

    Returns:
        (is_valid, error_message)
    """
    if not folders:
        return False, "請至少選擇一個資料夾"

    # 檢查資料夾是否存在
    for folder in folders:
        if not os.path.exists(folder):
            return False, f"資料夾不存在: {folder}"
        if not os.path.isdir(folder):
            return False, f"路徑不是資料夾: {folder}"

    # 檢查是否有重複路徑
    unique_folders = set(str(Path(f).resolve()) for f in folders)
    if len(unique_folders) < len(folders):
        return False, "來源清單有重複路徑"

    # 檢查是否有巢狀關係
    folders_list = list(unique_folders)
    for i, folder1 in enumerate(folders_list):
        for folder2 in folders_list[i+1:]:
            if is_nested_path(folder1, folder2):
                return False, f"資料夾之間有巢狀關係:\n{folder1}\n{folder2}"

    # 檢查是否與排除資料夾重疊
    if exclude_folders:
        for folder in folders_list:
            for exclude in exclude_folders:
                if is_nested_path(folder, exclude):
                    return False, f"來源資料夾與系統資料夾重疊:\n{folder}\n{exclude}"

    return True, ""


def check_add_new_folders(new_folder, disk_folders):
    """檢查照片新增模式的資料夾設定

    新照片資料夾可以放在硬碟資料夾裡面 (掃描硬碟時會跳過它),
    但不能與硬碟資料夾相同,硬碟資料夾也不能放在新照片資料夾裡面,
    否則同一個檔案會同時被當成新照片與硬碟照片,跟自己比對成重複。

    Args:
        new_folder: 新照片資料夾
        disk_folders: 硬碟資料夾清單

    Returns:
        (is_valid, error_message)
    """
    is_valid, error_msg = check_folders_validity(disk_folders)
    if not is_valid:
        return is_valid, error_msg

    new_path = Path(new_folder).resolve()
    for disk in disk_folders:
        disk_path = Path(disk).resolve()

        if disk_path == new_path:
            return False, f"新照片資料夾不能與硬碟資料夾相同:\n{disk}"

        try:
            disk_path.relative_to(new_path)
            return False, f"硬碟資料夾不能放在新照片資料夾裡面:\n{disk}\n{new_folder}"
        except ValueError:
            pass

    return True, ""
