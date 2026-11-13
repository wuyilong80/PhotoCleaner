"""檔案操作模組 - 處理移動、損壞檔案"""
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Callable, Optional
from ..utils.file_utils import get_output_folder_path, get_mirrored_dest_path, get_unique_path
from ..utils.constants import REMOVED_FOLDER_TEMPLATE, CORRUPTED_FOLDER_TEMPLATE
from .cache import CacheManager


class FileOperationManager:
    """檔案操作管理器"""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager

    def move_files_to_removed(self, file_paths: List[str],
                             progress_callback: Optional[Callable] = None) -> Tuple[int, List[str]]:
        """將檔案移動到待移除項目資料夾

        Args:
            file_paths: 要移動的檔案路徑清單
            progress_callback: 進度回呼 callback(current, total, file_path)

        Returns:
            (成功數量, 失敗的檔案清單)
        """
        # 建立移動清單
        move_list = []
        for file_path in file_paths:
            dest_path = get_mirrored_dest_path(file_path, REMOVED_FOLDER_TEMPLATE)
            move_list.append((file_path, dest_path))

        # 儲存到待執行清單
        self.cache_manager.save_pending_moves(move_list)

        # 執行移動
        success_count = 0
        failed_files = []
        total = len(move_list)

        for i, (source_path, dest_path) in enumerate(move_list, 1):
            if progress_callback:
                progress_callback(i, total, source_path)

            try:
                self._move_without_overwrite(source_path, dest_path)

                # 標記為已完成
                self.cache_manager.mark_move_completed(source_path)
                success_count += 1

            except Exception as e:
                failed_files.append(f"{source_path}: {str(e)}")

        # 全部完成後清除移動記錄
        if not failed_files:
            self.cache_manager.clear_pending_moves()

        return success_count, failed_files

    def _move_without_overwrite(self, source_path: str, dest_path: str) -> str:
        """移動檔案,目的地已有同名檔案時自動改名,絕不覆蓋

        Returns:
            實際的目的地路徑
        """
        # 確保目標資料夾存在
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        dest_path = get_unique_path(dest_path)
        shutil.move(source_path, dest_path)
        return dest_path

    def move_corrupted_file(self, file_path: str, error_msg: str = ""):
        """將損壞的檔案移動到損壞檔案資料夾

        Args:
            file_path: 檔案路徑
            error_msg: 錯誤訊息 (可選)
        """
        try:
            dest_path = self._move_without_overwrite(
                file_path, get_mirrored_dest_path(file_path, CORRUPTED_FOLDER_TEMPLATE)
            )

            # 可選:記錄錯誤訊息到同名的 .txt 檔案
            if error_msg:
                error_log_path = dest_path + '.error.txt'
                with open(error_log_path, 'w', encoding='utf-8') as f:
                    f.write(f"檔案: {file_path}\n")
                    f.write(f"錯誤: {error_msg}\n")
                    f.write(f"時間: {datetime.now().isoformat()}\n")

        except Exception:
            # 如果移動失敗,靜默處理
            pass

    def resume_pending_moves(self, progress_callback: Optional[Callable] = None) -> Tuple[int, List[str]]:
        """恢復未完成的移動操作

        Args:
            progress_callback: 進度回呼 callback(current, total, file_path)

        Returns:
            (成功數量, 失敗的檔案清單)
        """
        pending = self.cache_manager.get_pending_moves()

        if not pending:
            return 0, []

        success_count = 0
        failed_files = []
        total = len(pending)

        for i, (source_path, dest_path) in enumerate(pending, 1):
            if progress_callback:
                progress_callback(i, total, source_path)

            try:
                # 檢查來源檔案是否還存在
                if not os.path.exists(source_path):
                    # 檔案已經被移動或刪除,標記為完成
                    self.cache_manager.mark_move_completed(source_path)
                    success_count += 1
                    continue

                self._move_without_overwrite(source_path, dest_path)

                # 標記為已完成
                self.cache_manager.mark_move_completed(source_path)
                success_count += 1

            except Exception as e:
                failed_files.append(f"{source_path}: {str(e)}")

        # 全部完成後清除移動記錄
        if not failed_files:
            self.cache_manager.clear_pending_moves()

        return success_count, failed_files

    def get_removed_folders_for_sources(self, source_folders: List[str]) -> List[str]:
        """取得來源資料夾對應的待移除項目資料夾清單

        Args:
            source_folders: 來源資料夾清單

        Returns:
            待移除項目資料夾路徑清單
        """
        removed_folders = set()
        for source in source_folders:
            removed_folder = get_output_folder_path(source, REMOVED_FOLDER_TEMPLATE)
            removed_folders.add(removed_folder)

        return list(removed_folders)

    def get_corrupted_folders_for_sources(self, source_folders: List[str]) -> List[str]:
        """取得來源資料夾對應的損壞檔案資料夾清單

        Args:
            source_folders: 來源資料夾清單

        Returns:
            損壞檔案資料夾路徑清單
        """
        corrupted_folders = set()
        for source in source_folders:
            corrupted_folder = get_output_folder_path(source, CORRUPTED_FOLDER_TEMPLATE)
            corrupted_folders.add(corrupted_folder)

        return list(corrupted_folders)
