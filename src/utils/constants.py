"""常數定義"""
import os
from pathlib import Path

# 支援的檔案格式
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.heic', '.png'}
VIDEO_EXTENSIONS = {'.mov', '.mp4', '.avi'}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# 快取資料庫路徑
CACHE_DB_PATH = os.path.expanduser('~/.photo_dedup_cache.db')

# 資料夾名稱模板
REMOVED_FOLDER_TEMPLATE = "待移除項目_{date}"
CORRUPTED_FOLDER_TEMPLATE = "損壞檔案_{date}"

# 縮圖大小
THUMBNAIL_SIZE = (500, 500)

# 模式
MODE_ORGANIZE = "照片整理"
MODE_ADD_NEW = "照片新增"

# 檔案大小格式化
def format_file_size(size_bytes):
    """將位元組轉換為人類可讀的格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"
