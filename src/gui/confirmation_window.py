"""確認視窗 - 照片整理模式的重複檔案確認介面"""
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
from pathlib import Path
from typing import List, Dict, Callable
from ..utils.constants import format_file_size, THUMBNAIL_SIZE


class ConfirmationWindow(ctk.CTkToplevel):
    """照片整理模式的確認視窗"""

    def __init__(self, parent, duplicate_groups: List[List[str]],
                 on_confirm_callback: Callable, cache_manager=None,
                 resume_group_index: int = 0, resume_completed_groups: set = None,
                 resume_selected_files: List[str] = None):
        """
        Args:
            parent: 父視窗
            duplicate_groups: 重複檔案分組 [[file1, file2], ...]
            on_confirm_callback: 確認回呼 callback(files_to_remove)
            cache_manager: 快取管理器 (用於儲存進度)
            resume_group_index: 恢復的組別索引
            resume_completed_groups: 恢復的已完成組別集合
            resume_selected_files: 恢復的已選擇檔案清單
        """
        super().__init__(parent)

        self.title("Photo Cleaner - 確認重複檔案")
        self.geometry("1000x700")

        self.duplicate_groups = duplicate_groups
        self.on_confirm_callback = on_confirm_callback
        self.cache_manager = cache_manager

        self.current_group_index = resume_group_index
        self.completed_groups = resume_completed_groups if resume_completed_groups else set()
        self.files_to_remove = resume_selected_files if resume_selected_files else []

        # 當前組別的勾選狀態
        self.current_checkboxes = []
        self.current_checkbox_vars = []

        # 建立 UI
        self._create_ui()

        # 顯示當前組
        self._show_current_group()

        # 綁定關閉事件,自動儲存進度
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # 綁定鍵盤快捷鍵 - 使用 bind_all 確保在任何控件都能響應
        self.bind_all('<Left>', self._key_previous, '+')
        self.bind_all('<Right>', self._key_next, '+')
        self.bind_all('<Return>', self._key_next, '+')
        self.bind_all('<space>', self._key_next, '+')
        # 使用 Key 事件，不區分大小寫
        self.bind_all('<Key>', self._key_handler, '+')

    def _create_ui(self):
        """建立使用者介面"""
        # 頂部資訊區域
        info_frame = ctk.CTkFrame(self)
        info_frame.pack(pady=10, padx=20, fill="x")

        self.info_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.info_label.pack(pady=10)

        # 中間顯示區域 (可捲動)
        self.display_frame = ctk.CTkScrollableFrame(self, label_text="重複檔案")
        self.display_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # 快捷鍵說明
        shortcut_frame = ctk.CTkFrame(self)
        shortcut_frame.pack(pady=5, padx=20, fill="x")

        shortcut_label = ctk.CTkLabel(
            shortcut_frame,
            text="快捷鍵: 數字 1-9 選擇照片  |  ← → 上/下一組  |  Enter / Space 下一組",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        shortcut_label.pack(pady=5)

        # 底部按鈕區域
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=10, padx=20, fill="x")

        # 左側按鈕組
        left_buttons = ctk.CTkFrame(button_frame)
        left_buttons.pack(side="left")

        self.prev_button = ctk.CTkButton(
            left_buttons,
            text="← 上一組 (A)",
            command=self._show_previous_group,
            width=130
        )
        self.prev_button.pack(side="left", padx=5)

        self.next_button = ctk.CTkButton(
            left_buttons,
            text="下一組 (D) →",
            command=self._show_next_group,
            width=130
        )
        self.next_button.pack(side="left", padx=5)

        # 右側完成按鈕
        self.finish_button = ctk.CTkButton(
            button_frame,
            text="完成確認",
            command=self._finish_confirmation,
            width=120,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.finish_button.pack(side="right", padx=5)

    def _show_current_group(self):
        """顯示當前組別的檔案"""
        # 更新資訊標籤
        total_groups = len(self.duplicate_groups)
        progress_percent = int((len(self.completed_groups) / total_groups) * 100) if total_groups > 0 else 0
        self.info_label.configure(
            text=f"第 {self.current_group_index + 1} / {total_groups} 組   "
                 f"已完成: {len(self.completed_groups)} ({progress_percent}%)"
        )

        # 更新按鈕狀態
        self._update_button_states()

        # 清除舊的顯示
        for widget in self.display_frame.winfo_children():
            widget.destroy()

        self.current_checkboxes = []
        self.current_checkbox_vars = []

        # 取得當前組別的檔案
        files = self.duplicate_groups[self.current_group_index]

        # 統一使用橫向並排顯示
        self._show_files_side_by_side(files)

        # 更新按鈕狀態
        self.prev_button.configure(state="normal" if self.current_group_index > 0 else "disabled")
        self.next_button.configure(
            state="normal" if self.current_group_index < len(self.duplicate_groups) - 1 else "disabled"
        )

    def _show_files_side_by_side(self, files: List[str]):
        """並排顯示檔案（橫向排列，可水平滑動）"""
        import tkinter as tk

        # 創建外層容器
        outer_container = ctk.CTkFrame(self.display_frame)
        outer_container.pack(pady=10, fill="both", expand=True)

        # 創建 Canvas（配合主題顏色）
        # 獲取當前主題的背景色
        try:
            theme_bg = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
            if isinstance(theme_bg, (list, tuple)):
                # 根據當前外觀模式選擇顏色
                mode = ctk.get_appearance_mode()
                bg_color = theme_bg[0] if mode == "Light" else theme_bg[1]
            else:
                bg_color = theme_bg
        except:
            bg_color = "#2b2b2b"  # 預設深色背景

        canvas = tk.Canvas(
            outer_container,
            highlightthickness=0,
            bg=bg_color
        )
        h_scrollbar = ctk.CTkScrollbar(outer_container, orientation="horizontal", command=canvas.xview)

        # 創建內部容器框架（放在 Canvas 中）
        inner_container = ctk.CTkFrame(canvas)

        # 配置 Canvas
        canvas.configure(xscrollcommand=h_scrollbar.set)

        # 放置滾動條和 Canvas
        h_scrollbar.pack(side="bottom", fill="x", padx=10)
        canvas.pack(side="top", fill="both", expand=True)

        # 將內部容器放入 Canvas
        canvas_frame = canvas.create_window((0, 0), window=inner_container, anchor="nw")

        # 添加檔案
        for i, file_path in enumerate(files):
            file_frame = ctk.CTkFrame(inner_container)
            file_frame.pack(side="left", padx=10, pady=10)

            self._create_file_widget(file_frame, file_path, i)

        # 更新內部容器的大小和 Canvas 滾動區域
        def configure_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # 確保 canvas 高度適應內容
            canvas.configure(height=inner_container.winfo_reqheight())

        inner_container.bind("<Configure>", configure_scroll_region)

    def _create_file_widget(self, parent_frame, file_path: str, index: int):
        """建立單個檔案的顯示元件"""
        # 檢查此檔案是否已經被選擇要移除
        is_selected = file_path in self.files_to_remove

        # 勾選框
        var = ctk.BooleanVar(value=is_selected)

        # 綁定勾選框變化事件
        var.trace_add('write', lambda *args: self._on_checkbox_changed())

        checkbox = ctk.CTkCheckBox(
            parent_frame,
            text="選擇移除",
            variable=var,
            font=ctk.CTkFont(size=12)
        )
        checkbox.pack(anchor="w", padx=10, pady=5)

        self.current_checkbox_vars.append(var)
        self.current_checkboxes.append(checkbox)

        # 建立可點擊的容器框架
        clickable_frame = ctk.CTkFrame(parent_frame, cursor="hand2")
        clickable_frame.pack(padx=10, pady=5, fill="both", expand=True)

        # 綁定點擊事件到容器 - 切換勾選狀態
        def toggle_selection(event=None):
            var.set(not var.get())

        clickable_frame.bind("<Button-1>", toggle_selection)

        # 縮圖
        thumbnail_label = self._create_thumbnail(clickable_frame, file_path)
        if thumbnail_label:
            thumbnail_label.pack(padx=10, pady=5)
            # 縮圖也要能點擊
            thumbnail_label.bind("<Button-1>", toggle_selection)

        # 檔案資訊
        info_frame = ctk.CTkFrame(clickable_frame)
        info_frame.pack(padx=10, pady=5, fill="x")

        # 取得檔案資訊
        try:
            stat = os.stat(file_path)
            file_size = format_file_size(stat.st_size)
            file_name = os.path.basename(file_path)
            folder_path = os.path.dirname(file_path)
        except Exception:
            file_size = "無法取得"
            file_name = os.path.basename(file_path)
            folder_path = os.path.dirname(file_path)

        # 檔案名稱
        name_label = ctk.CTkLabel(
            info_frame,
            text=f"檔案名稱: {file_name}",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        name_label.pack(fill="x", padx=5, pady=2)
        name_label.bind("<Button-1>", toggle_selection)

        # 路徑（可點擊）
        path_frame = ctk.CTkFrame(info_frame)
        path_frame.pack(fill="x", padx=5, pady=2)

        path_label_text = ctk.CTkLabel(
            path_frame,
            text="路徑: ",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        path_label_text.pack(side="left")
        path_label_text.bind("<Button-1>", toggle_selection)

        path_button = ctk.CTkLabel(
            path_frame,
            text=folder_path,
            font=ctk.CTkFont(size=12),
            anchor="w",
            text_color=("#1f6aa5", "#4a9eff"),
            cursor="hand2"
        )
        path_button.pack(side="left", fill="x", expand=True)

        def open_folder(event=None):
            import subprocess
            subprocess.run(["open", folder_path])
            return "break"

        path_button.bind("<Button-1>", open_folder)

        # 檔案大小
        size_label = ctk.CTkLabel(
            info_frame,
            text=f"檔案大小: {file_size}",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        size_label.pack(fill="x", padx=5, pady=2)
        size_label.bind("<Button-1>", toggle_selection)

    def _create_thumbnail(self, parent_frame, file_path: str):
        """建立縮圖"""
        try:
            # 檢查是否為圖片格式
            ext = Path(file_path).suffix.lower()
            if ext in {'.jpg', '.jpeg', '.png'}:
                # 載入圖片
                img = Image.open(file_path)
                img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

                # 轉換為 CTkImage
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)

                label = ctk.CTkLabel(parent_frame, image=ctk_img, text="")
                label.image = ctk_img  # 保持引用
                return label

            elif ext == '.heic':
                # HEIC 格式需要特殊處理
                try:
                    from pillow_heif import register_heif_opener
                    register_heif_opener()

                    img = Image.open(file_path)
                    img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)

                    label = ctk.CTkLabel(parent_frame, image=ctk_img, text="")
                    label.image = ctk_img
                    return label

                except ImportError:
                    # pillow-heif 未安裝
                    pass

            elif ext in {'.mov', '.mp4', '.avi'}:
                # 影片格式，嘗試擷取第一個畫面
                try:
                    import cv2
                    import numpy as np

                    # 開啟影片檔案
                    cap = cv2.VideoCapture(file_path)

                    # 讀取第一個畫面
                    ret, frame = cap.read()
                    cap.release()

                    if ret:
                        # 將 BGR 轉換為 RGB
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                        # 轉換為 PIL Image
                        img = Image.fromarray(frame_rgb)
                        img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

                        # 轉換為 CTkImage
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)

                        label = ctk.CTkLabel(parent_frame, image=ctk_img, text="")
                        label.image = ctk_img
                        return label

                except (ImportError, Exception):
                    # OpenCV 未安裝或讀取失敗
                    pass

            # 影片或無法載入的格式,顯示佔位符
            placeholder = ctk.CTkLabel(
                parent_frame,
                text="[影片檔案或縮圖載入失敗]",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            return placeholder

        except Exception:
            # 載入失敗
            placeholder = ctk.CTkLabel(
                parent_frame,
                text="[縮圖載入失敗]",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            return placeholder

    def _on_checkbox_changed(self):
        """勾選框變化時的處理"""
        # 取得當前組別的檔案
        files = self.duplicate_groups[self.current_group_index]

        # 檢查勾選狀態
        selected_indices = [i for i, var in enumerate(self.current_checkbox_vars) if var.get()]

        # 先移除該組中所有之前的選擇
        for file_path in files:
            if file_path in self.files_to_remove:
                self.files_to_remove.remove(file_path)

        # 檢查選擇狀態
        if len(selected_indices) == 0:
            # 沒有選擇任何檔案，取消該組的完成標記
            if self.current_group_index in self.completed_groups:
                self.completed_groups.remove(self.current_group_index)
            self._update_button_states()
            self._save_progress()
            return

        if len(selected_indices) == len(files) and len(files) > 0:
            # 全選是錯誤狀態，取消該組的完成標記
            if self.current_group_index in self.completed_groups:
                self.completed_groups.remove(self.current_group_index)
            self._update_button_states()
            self._save_progress()
            return

        # 有效選擇：記錄目前選擇要移除的檔案
        for i in selected_indices:
            file_path = files[i]
            if file_path not in self.files_to_remove:
                self.files_to_remove.append(file_path)

        # 標記為已完成
        self.completed_groups.add(self.current_group_index)

        # 自動儲存進度
        self._save_progress()

        # 更新按鈕狀態
        self._update_button_states()

    def _update_button_states(self):
        """更新按鈕狀態"""
        total_groups = len(self.duplicate_groups)

        # 更新完成按鈕狀態 - 所有組都已完成才能點擊
        if len(self.completed_groups) == total_groups:
            self.finish_button.configure(state="normal")
        else:
            self.finish_button.configure(state="disabled")

    def _show_next_group(self):
        """顯示下一組"""
        # 先確認當前組別
        if not self._confirm_current_group():
            return

        # 移到下一組
        if self.current_group_index < len(self.duplicate_groups) - 1:
            self.current_group_index += 1
            self._show_current_group()
        else:
            # 已經是最後一組，只更新按鈕狀態
            self._show_current_group()

    def _show_previous_group(self):
        """顯示上一組"""
        # 先確認當前組別
        if not self._confirm_current_group():
            return

        # 移到上一組
        if self.current_group_index > 0:
            self.current_group_index -= 1
            self._show_current_group()

    def _confirm_current_group(self) -> bool:
        """確認當前組別的選擇

        Returns:
            True 如果確認成功,False 如果有錯誤
        """
        # 取得當前組別的檔案
        files = self.duplicate_groups[self.current_group_index]

        # 檢查勾選狀態
        selected_indices = [i for i, var in enumerate(self.current_checkbox_vars) if var.get()]

        # 防呆檢查：不能不選
        if len(selected_indices) == 0:
            messagebox.showerror("錯誤", "至少選擇一張要移除的照片!")
            return False

        # 防呆檢查：不能全選
        if len(selected_indices) == len(files) and len(files) > 0:
            messagebox.showerror("錯誤", "至少保留一張照片!")
            return False

        # 其他情況都已經在 _on_checkbox_changed 中處理過了
        return True

    def _finish_confirmation(self):
        """完成確認"""
        # 清除進度 (因為已經完成)
        if self.cache_manager:
            from ..utils.constants import MODE_ORGANIZE
            self.cache_manager.clear_confirmation_progress(MODE_ORGANIZE)

        # 解綁快捷鍵
        self._unbind_shortcuts()

        # 呼叫回呼函數
        self.on_confirm_callback(self.files_to_remove)

        # 關閉視窗
        self.destroy()

    def _save_progress(self):
        """儲存確認進度到快取"""
        if not self.cache_manager:
            return

        # 準備要儲存的重複組別資料
        duplicate_groups_data = [
            {
                'files': group,
                'index': i
            }
            for i, group in enumerate(self.duplicate_groups)
        ]

        # 建立已選擇檔案的映射 {組別索引: [要移除的檔案路徑]}
        selected_files_map = {}
        for group_idx in self.completed_groups:
            group_files = self.duplicate_groups[group_idx]
            selected_in_group = [f for f in group_files if f in self.files_to_remove]
            if selected_in_group:
                selected_files_map[group_idx] = selected_in_group

        from ..utils.constants import MODE_ORGANIZE

        # 將選擇記錄加入資料
        progress_data = {
            'duplicate_groups': duplicate_groups_data,
            'completed_groups': list(self.completed_groups),
            'selected_files_map': selected_files_map
        }

        self.cache_manager.save_confirmation_progress(
            mode=MODE_ORGANIZE,
            current_group=self.current_group_index,
            total_groups=len(self.duplicate_groups),
            duplicate_groups=progress_data,
            completed_groups=list(self.completed_groups)
        )

    def _key_handler(self, event):
        """統一處理所有按鍵事件"""
        if not self.winfo_exists():
            return

        # 使用 keysym 來判斷，更可靠
        key = event.keysym.lower()

        # 處理數字鍵 1-9 選擇照片
        if key.isdigit():
            index = int(key) - 1  # 1對應索引0, 2對應索引1...
            if 0 <= index < len(self.current_checkbox_vars):
                # 切換該照片的勾選狀態
                current_value = self.current_checkbox_vars[index].get()
                self.current_checkbox_vars[index].set(not current_value)
                return "break"

        # 處理字母鍵（如果有英文輸入法）
        if key == 'a':
            self._show_previous_group()
            return "break"
        elif key == 'd':
            self._show_next_group()
            return "break"

    def _key_previous(self, event):
        """上一組快捷鍵處理"""
        if self.winfo_exists():
            self._show_previous_group()
        return "break"

    def _key_next(self, event):
        """下一組快捷鍵處理"""
        if self.winfo_exists():
            self._show_next_group()
        return "break"

    def _unbind_shortcuts(self):
        """解綁所有快捷鍵"""
        try:
            self.unbind_all('<Left>')
            self.unbind_all('<Right>')
            self.unbind_all('<Return>')
            self.unbind_all('<space>')
            self.unbind_all('<Key>')
        except:
            pass

    def _on_closing(self):
        """視窗關閉時的處理"""
        # 儲存當前進度
        self._save_progress()

        # 解綁快捷鍵
        self._unbind_shortcuts()

        # 關閉視窗
        self.destroy()
