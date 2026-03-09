"""檔案掃描與 SHA-256 計算模組"""
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Callable, Optional
from ..utils.file_utils import is_supported_file, should_skip_file, should_skip_directory
from ..utils.constants import CORRUPTED_FOLDER_TEMPLATE
from .cache import CacheManager


class FileScanner:
    """檔案掃描器"""

    def __init__(self, cache_manager: CacheManager, corrupted_handler=None):
        """
        Args:
            cache_manager: 快取管理器
            corrupted_handler: 損壞檔案處理函數 callback(file_path, error)
        """
        self.cache_manager = cache_manager
        self.corrupted_handler = corrupted_handler

    def scan_folders(self, folders: List[str],
                    progress_callback: Optional[Callable] = None) -> Dict[str, Dict]:
        """掃描資料夾,計算所有檔案的 SHA-256

        Args:
            folders: 要掃描的資料夾清單
            progress_callback: 進度回呼函數 callback(current, total, file_path, eta_seconds)

        Returns:
            {file_path: {'sha256': str, 'size': int, 'mtime': float}, ...}
        """
        # 第一階段:收集所有檔案
        all_files = []
        for folder in folders:
            files = self._collect_files(folder)
            all_files.extend(files)

        total_files = len(all_files)

        # 第二階段:計算雜湊值
        file_info_dict = {}
        processed_count = 0

        import time
        start_time = time.time()

        for file_path in all_files:
            processed_count += 1

            # 計算預估剩餘時間
            elapsed = time.time() - start_time
            if processed_count > 1:
                avg_time_per_file = elapsed / (processed_count - 1)
                remaining_files = total_files - processed_count
                eta_seconds = avg_time_per_file * remaining_files
            else:
                eta_seconds = 0

            # 回報進度
            if progress_callback:
                progress_callback(processed_count, total_files, file_path, eta_seconds)

            try:
                # 取得檔案資訊
                stat = os.stat(file_path)
                file_size = stat.st_size
                mtime = stat.st_mtime

                # 嘗試從快取取得雜湊值
                cached_hash = self.cache_manager.get_file_hash(file_path, file_size, mtime)

                if cached_hash:
                    sha256_hash = cached_hash
                else:
                    # 計算雜湊值
                    sha256_hash = self._calculate_sha256(file_path)

                    # 儲存到快取
                    self.cache_manager.save_file_hash(file_path, file_size, mtime, sha256_hash)

                file_info_dict[file_path] = {
                    'sha256': sha256_hash,
                    'size': file_size,
                    'mtime': mtime
                }

            except Exception as e:
                # 處理損壞檔案
                if self.corrupted_handler:
                    self.corrupted_handler(file_path, str(e))

        return file_info_dict

    def _collect_files(self, root_folder: str) -> List[str]:
        """遞迴收集所有支援的檔案

        Args:
            root_folder: 根資料夾

        Returns:
            檔案路徑清單
        """
        files = []

        try:
            for entry in os.scandir(root_folder):
                # 跳過隱藏項目和符號連結
                if entry.name.startswith('.') or entry.is_symlink():
                    continue

                if entry.is_dir():
                    # 遞迴掃描子資料夾
                    if not should_skip_directory(entry.path):
                        files.extend(self._collect_files(entry.path))

                elif entry.is_file():
                    # 檢查是否為支援的檔案格式
                    if not should_skip_file(entry.path) and is_supported_file(entry.path):
                        files.append(entry.path)

        except PermissionError:
            # 忽略沒有權限的資料夾
            pass
        except Exception:
            # 忽略其他錯誤
            pass

        return files

    def _calculate_sha256(self, file_path: str) -> str:
        """計算檔案的 SHA-256 雜湊值

        Args:
            file_path: 檔案路徑

        Returns:
            SHA-256 雜湊值 (hex string)
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, 'rb') as f:
            # 分塊讀取,避免大檔案佔用過多記憶體
            for chunk in iter(lambda: f.read(4096 * 1024), b''):  # 4MB chunks
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()


class DeduplicateFinder:
    """去重檢測器"""

    @staticmethod
    def find_duplicates(file_info_dict: Dict[str, Dict]) -> List[List[str]]:
        """找出重複的檔案

        Args:
            file_info_dict: {file_path: {'sha256': str, 'size': int, ...}, ...}

        Returns:
            重複檔案分組 [[file1, file2], [file3, file4, file5], ...]
        """
        # 以 SHA-256 分組
        hash_groups = {}
        for file_path, info in file_info_dict.items():
            sha256 = info['sha256']
            if sha256 not in hash_groups:
                hash_groups[sha256] = []
            hash_groups[sha256].append(file_path)

        # 只保留重複的組別 (超過 1 個檔案)
        duplicate_groups = [
            files for files in hash_groups.values()
            if len(files) > 1
        ]

        return duplicate_groups

    @staticmethod
    def find_new_duplicates(new_folder_files: Dict[str, Dict],
                           disk_folder_files: Dict[str, Dict]) -> List[str]:
        """找出新照片資料夾中與硬碟重複的檔案

        Args:
            new_folder_files: 新照片資料夾的檔案資訊
            disk_folder_files: 硬碟資料夾的檔案資訊

        Returns:
            新照片資料夾中重複的檔案路徑清單
        """
        # 建立硬碟資料夾的雜湊集合
        disk_hashes = set(info['sha256'] for info in disk_folder_files.values())

        # 找出新照片中與硬碟重複的檔案
        duplicate_new_files = []
        for file_path, info in new_folder_files.items():
            if info['sha256'] in disk_hashes:
                duplicate_new_files.append(file_path)

        return duplicate_new_files
