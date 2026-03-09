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


def path_to_filename(file_path):
    """將路徑轉換為安全的檔案名稱

    例如: /Volumes/HDD/旅遊/IMG_0001.jpg -> Volumes_HDD_旅遊_IMG_0001.jpg
    """
    path = Path(file_path)

    # 移除開頭的 /
    path_str = str(path.resolve()).lstrip('/')

    # 將 / 替換為 _
    safe_name = path_str.replace('/', '_')

    return safe_name


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
