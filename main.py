"""Photo Deduplicator - 主程式入口"""
import sys
import threading
from tkinter import messagebox

# 檢查並安裝必要的套件
def check_and_install_packages():
    """檢查並安裝必要的套件"""
    required_packages = [
        ('customtkinter', 'customtkinter'),
        ('PIL', 'pillow'),
        ('pillow_heif', 'pillow-heif')
    ]

    missing_packages = []

    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)

    if missing_packages:
        print("正在安裝必要的套件...")
        import subprocess
        for package in missing_packages:
            print(f"安裝 {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print("套件安裝完成!")

# 啟動時檢查套件
check_and_install_packages()

import customtkinter as ctk
from src.core.cache import CacheManager
from src.core.scanner import FileScanner, DeduplicateFinder
from src.core.file_operations import FileOperationManager
from src.gui.main_window import MainWindow
from src.gui.confirmation_window import ConfirmationWindow
from src.gui.progress_dialog import (
    ProgressDialog,
    AddNewModeResultDialog,
    CompletionDialog
)
from src.utils.constants import MODE_ORGANIZE, MODE_ADD_NEW


class PhotoDeduplicatorApp:
    """照片去重應用程式"""

    def __init__(self):
        self.cache_manager = CacheManager()
        self.file_op_manager = FileOperationManager(self.cache_manager)

        # 建立主視窗
        self.main_window = MainWindow()

        # 設定回呼函數
        self.main_window.set_start_organize_callback(self.start_organize_mode)
        self.main_window.set_start_add_new_callback(self.start_add_new_mode)
        self.main_window.set_resume_progress_callback(self.resume_progress)
        self.main_window.set_clear_cache_callback(self.clear_cache)
        self.main_window.set_check_cache_callback(self.check_cache)

        # 檢查是否有未完成的移動操作
        self._check_pending_moves()

        # 更新快取按鈕狀態
        self.main_window.update_cache_buttons()

    def run(self):
        """執行應用程式"""
        self.main_window.mainloop()

    def _check_pending_moves(self):
        """檢查是否有未完成的移動操作"""
        if self.cache_manager.has_pending_moves():
            result = messagebox.askyesno(
                "提示",
                "上次有未完成的操作,是否繼續?"
            )
            if result:
                # 在背景執行恢復操作
                threading.Thread(
                    target=self._resume_pending_moves,
                    daemon=True
                ).start()
            else:
                # 清除未完成的操作
                self.cache_manager.clear_pending_moves()

    def _resume_pending_moves(self):
        """恢復未完成的移動操作"""
        # 建立進度對話框
        progress = ProgressDialog(self.main_window, "恢復移動操作")

        def progress_callback(current, total, file_path):
            progress.update_progress(current, total, "恢復移動檔案", file_path)

        success_count, failed = self.file_op_manager.resume_pending_moves(progress_callback)

        progress.close_dialog()

        if failed:
            messagebox.showerror("錯誤", f"部分檔案移動失敗:\n" + "\n".join(failed[:5]))
        else:
            messagebox.showinfo("完成", f"成功恢復 {success_count} 個檔案的移動操作")

    # === 快取管理 ===

    def check_cache(self):
        """檢查是否有未完成的確認進度

        Returns:
            (has_progress, mode) 或 (False, None)
        """
        # 檢查照片整理模式
        organize_progress = self.cache_manager.load_confirmation_progress(MODE_ORGANIZE)

        # 檢查照片新增模式
        add_new_progress = self.cache_manager.load_confirmation_progress(MODE_ADD_NEW)

        # 如果兩種模式都有進度，返回更新時間較晚的
        if organize_progress and add_new_progress:
            # 比較更新時間（這裡簡化處理，返回照片整理模式）
            return (True, MODE_ORGANIZE)
        elif organize_progress:
            return (True, MODE_ORGANIZE)
        elif add_new_progress:
            return (True, MODE_ADD_NEW)
        else:
            return (False, None)

    def resume_progress(self):
        """繼續上次未完成的處理"""
        # 檢查照片整理模式進度
        organize_progress = self.cache_manager.load_confirmation_progress(MODE_ORGANIZE)

        # 檢查照片新增模式進度
        add_new_progress = self.cache_manager.load_confirmation_progress(MODE_ADD_NEW)

        # 決定恢復哪個模式
        if organize_progress and add_new_progress:
            # 如果兩種都有，讓用戶選擇
            result = messagebox.askyesno(
                "選擇模式",
                "發現兩種模式都有未完成進度，是否恢復「照片整理」模式？\n\n"
                "「是」：恢復照片整理模式\n「否」：恢復照片新增模式"
            )
            mode = MODE_ORGANIZE if result else MODE_ADD_NEW
        elif organize_progress:
            mode = MODE_ORGANIZE
        elif add_new_progress:
            mode = MODE_ADD_NEW
        else:
            messagebox.showinfo("提示", "沒有未完成的確認進度")
            return

        # 自動切換到對應模式
        self.main_window.current_mode.set(mode)

        if mode == MODE_ORGANIZE:
            self._resume_organize_progress(organize_progress)
        else:
            self._resume_add_new_progress(add_new_progress)

    def _resume_organize_progress(self, progress_data):
        """恢復照片整理模式進度"""
        current_group, total_groups, duplicate_groups_data, completed_groups = progress_data

        # 恢復進度
        # 處理新舊格式兼容
        if isinstance(duplicate_groups_data, dict):
            # 新格式
            duplicate_groups = [group_data['files'] for group_data in duplicate_groups_data['duplicate_groups']]
            selected_files_map = duplicate_groups_data.get('selected_files_map', {})

            # 重建已選擇的檔案清單
            selected_files = []
            for files_list in selected_files_map.values():
                selected_files.extend(files_list)
        else:
            # 舊格式
            duplicate_groups = [group_data['files'] for group_data in duplicate_groups_data]
            selected_files = []

        messagebox.showinfo(
            "恢復進度 - 照片整理模式",
            f"將從第 {current_group + 1}/{total_groups} 組繼續\n已完成: {len(completed_groups)} 組"
        )

        self._show_organize_confirmation(
            duplicate_groups, current_group, set(completed_groups), selected_files
        )

    def _resume_add_new_progress(self, progress_data):
        """恢復照片新增模式進度"""
        # 照片新增模式沒有逐組確認流程，所以這裡只是清除進度
        messagebox.showinfo(
            "提示",
            "照片新增模式不支援進度恢復\n（此模式是一次性確認所有重複檔案）\n\n將清除此進度。"
        )
        self.cache_manager.clear_confirmation_progress(MODE_ADD_NEW)
        self.main_window.update_cache_buttons()

    def clear_cache(self):
        """清除所有快取"""
        import os

        try:
            # 關閉資料庫連接
            self.cache_manager = None

            # 刪除快取檔案
            from src.utils.constants import CACHE_DB_PATH
            if os.path.exists(CACHE_DB_PATH):
                os.remove(CACHE_DB_PATH)

            # 重新建立 cache_manager
            self.cache_manager = CacheManager()
            self.file_op_manager = FileOperationManager(self.cache_manager)

            messagebox.showinfo("完成", "快取已清除")
            self.main_window.update_cache_buttons()

        except Exception as e:
            messagebox.showerror("錯誤", f"清除快取失敗: {str(e)}")

    # === 照片整理模式 ===

    def start_organize_mode(self, source_folders):
        """開始照片整理模式"""
        # 在背景執行掃描
        threading.Thread(
            target=self._scan_organize_mode,
            args=(source_folders,),
            daemon=True
        ).start()

    def _scan_organize_mode(self, source_folders):
        """掃描照片整理模式 (背景執行)"""
        # 建立進度對話框
        progress = ProgressDialog(self.main_window, "掃描中")

        # 建立掃描器
        def corrupted_handler(file_path, error):
            self.file_op_manager.move_corrupted_file(file_path, error)

        scanner = FileScanner(self.cache_manager, corrupted_handler)

        # 進度回呼
        def progress_callback(current, total, file_path, eta_seconds):
            progress.update_progress(
                current, total, "掃描檔案", file_path, eta_seconds
            )

        # 掃描所有資料夾
        file_info = scanner.scan_folders(source_folders, progress_callback)

        # 關閉進度對話框
        progress.close_dialog()

        # 找出重複檔案
        duplicate_groups = DeduplicateFinder.find_duplicates(file_info)

        # 顯示結果
        if not duplicate_groups:
            messagebox.showinfo("完成", "未發現重複照片")
            return

        # 開啟確認介面
        self.main_window.after(
            0,
            lambda: self._show_organize_confirmation(duplicate_groups)
        )

    def _show_organize_confirmation(self, duplicate_groups, resume_group_index=0,
                                   resume_completed_groups=None, resume_selected_files=None):
        """顯示照片整理模式的確認介面"""
        def on_confirm(files_to_remove):
            if not files_to_remove:
                messagebox.showinfo("完成", "沒有選擇要移除的檔案")
                # 更新快取按鈕狀態
                self.main_window.update_cache_buttons()
                return

            # 在背景執行移動操作
            threading.Thread(
                target=self._move_files_to_removed,
                args=(files_to_remove,),
                daemon=True
            ).start()

        ConfirmationWindow(
            self.main_window,
            duplicate_groups,
            on_confirm,
            self.cache_manager,
            resume_group_index,
            resume_completed_groups,
            resume_selected_files
        )

        # 當確認視窗關閉時更新快取按鈕
        def update_buttons_on_close():
            self.main_window.after(100, self.main_window.update_cache_buttons)

        self.main_window.after(100, update_buttons_on_close)

    def _move_files_to_removed(self, files_to_remove):
        """移動檔案到待移除項目資料夾 (背景執行)"""
        # 建立進度對話框
        progress = ProgressDialog(self.main_window, "移動檔案")

        def progress_callback(current, total, file_path):
            progress.update_progress(current, total, "移動檔案", file_path)

        success_count, failed = self.file_op_manager.move_files_to_removed(
            files_to_remove, progress_callback
        )

        progress.close_dialog()

        # 顯示結果
        if failed:
            messagebox.showerror(
                "部分失敗",
                f"成功移動 {success_count} 個檔案,但以下檔案失敗:\n" + "\n".join(failed[:5])
            )
        else:
            messagebox.showinfo("完成", f"成功移動 {success_count} 個檔案到待移除項目資料夾")

        # 更新快取按鈕狀態
        self.main_window.update_cache_buttons()

    # === 照片新增模式 ===

    def start_add_new_mode(self, new_folder, disk_folders):
        """開始照片新增模式"""
        # 在背景執行掃描
        threading.Thread(
            target=self._scan_add_new_mode,
            args=(new_folder, disk_folders),
            daemon=True
        ).start()

    def _scan_add_new_mode(self, new_folder, disk_folders):
        """掃描照片新增模式 (背景執行)"""
        # 建立進度對話框
        progress = ProgressDialog(self.main_window, "掃描中")

        # 建立掃描器
        def corrupted_handler(file_path, error):
            self.file_op_manager.move_corrupted_file(file_path, error)

        scanner = FileScanner(self.cache_manager, corrupted_handler)

        # 掃描新照片資料夾
        def progress_callback_new(current, total, file_path, eta_seconds):
            progress.update_progress(
                current, total, "掃描新照片資料夾", file_path, eta_seconds
            )

        new_folder_files = scanner.scan_folders([new_folder], progress_callback_new)

        # 掃描硬碟資料夾
        def progress_callback_disk(current, total, file_path, eta_seconds):
            progress.update_progress(
                current, total, "掃描硬碟資料夾", file_path, eta_seconds
            )

        # 新照片資料夾若放在硬碟資料夾裡面,掃描硬碟時跳過它,避免新照片跟自己比對
        disk_folder_files = scanner.scan_folders(
            disk_folders, progress_callback_disk, exclude_folders=[new_folder]
        )

        # 關閉進度對話框
        progress.close_dialog()

        # 找出重複檔案
        duplicate_files = DeduplicateFinder.find_new_duplicates(
            new_folder_files, disk_folder_files
        )

        # 顯示結果
        if not duplicate_files:
            messagebox.showinfo("完成", "未發現重複照片")
            return

        # 顯示確認對話框
        self.main_window.after(
            0,
            lambda: self._show_add_new_confirmation(duplicate_files)
        )

    def _show_add_new_confirmation(self, duplicate_files):
        """顯示照片新增模式的確認對話框"""
        def on_confirm():
            # 在背景執行移動操作
            threading.Thread(
                target=self._move_files_to_removed,
                args=(duplicate_files,),
                daemon=True
            ).start()

        AddNewModeResultDialog(
            self.main_window,
            len(duplicate_files),
            on_confirm
        )


def main():
    """主函數"""
    app = PhotoDeduplicatorApp()
    app.run()


if __name__ == "__main__":
    main()
