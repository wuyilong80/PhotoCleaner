"""主視窗 - 模式選擇與資料夾輸入"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import List, Callable
from ..utils.constants import MODE_ORGANIZE, MODE_ADD_NEW
from ..utils.file_utils import check_folders_validity, check_add_new_folders


class MainWindow(ctk.CTk):
    """主視窗"""

    def __init__(self):
        super().__init__()

        self.title("Photo Cleaner")
        self.geometry("900x700")

        # 設定最小視窗大小
        self.minsize(800, 600)

        # 設定主題
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # 當前模式
        self.current_mode = ctk.StringVar(value=MODE_ORGANIZE)

        # 資料夾清單
        self.source_folders = []  # 照片整理模式的來源資料夾
        self.new_folder = ""  # 照片新增模式的新照片資料夾
        self.disk_folders = []  # 照片新增模式的硬碟資料夾

        # 建立 UI
        self._create_ui()

        # 綁定模式切換
        self.current_mode.trace_add('write', self._on_mode_changed)

    def _create_ui(self):
        """建立使用者介面"""
        # 標題
        title_label = ctk.CTkLabel(
            self,
            text="照片整理工具",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=20)

        # 模式選擇
        mode_frame = ctk.CTkFrame(self)
        mode_frame.pack(pady=10, padx=20, fill="x")

        mode_label = ctk.CTkLabel(
            mode_frame,
            text="模式選擇:",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        mode_label.pack(side="left", padx=10)

        organize_radio = ctk.CTkRadioButton(
            mode_frame,
            text=MODE_ORGANIZE,
            variable=self.current_mode,
            value=MODE_ORGANIZE,
            font=ctk.CTkFont(size=14)
        )
        organize_radio.pack(side="left", padx=10)

        add_new_radio = ctk.CTkRadioButton(
            mode_frame,
            text=MODE_ADD_NEW,
            variable=self.current_mode,
            value=MODE_ADD_NEW,
            font=ctk.CTkFont(size=14)
        )
        add_new_radio.pack(side="left", padx=10)

        # 資料夾輸入區域 (會根據模式動態切換)
        self.folder_container = ctk.CTkFrame(self)
        self.folder_container.pack(pady=20, padx=20, fill="both", expand=True)

        # 初始化為照片整理模式
        self._show_organize_mode_ui()

        # 快取管理按鈕區域
        cache_frame = ctk.CTkFrame(self)
        cache_frame.pack(pady=10, padx=20, fill="x")

        self.resume_button = ctk.CTkButton(
            cache_frame,
            text="📂 繼續上次未完成的處理",
            command=self._on_resume_clicked,
            font=ctk.CTkFont(size=14),
            height=35,
            fg_color="#2B7A0B",
            hover_color="#1f5a08"
        )
        self.resume_button.pack(side="left", padx=5, fill="x", expand=True)

        self.clear_cache_button = ctk.CTkButton(
            cache_frame,
            text="🗑️ 清除快取",
            command=self._on_clear_cache_clicked,
            font=ctk.CTkFont(size=14),
            height=35,
            fg_color="#8B0000",
            hover_color="#660000"
        )
        self.clear_cache_button.pack(side="left", padx=5, fill="x", expand=True)

        # 開始掃描按鈕
        self.start_button = ctk.CTkButton(
            self,
            text="開始掃描",
            command=self._on_start_clicked,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40
        )
        self.start_button.pack(pady=20, padx=20, fill="x")

        # 更新快取按鈕狀態
        self._update_cache_buttons()

    def _on_mode_changed(self, *args):
        """模式切換時的處理"""
        # 清空所有資料夾
        self.source_folders = []
        self.new_folder = ""
        self.disk_folders = []

        # 清除舊的 UI
        for widget in self.folder_container.winfo_children():
            widget.destroy()

        # 根據模式顯示對應的 UI
        if self.current_mode.get() == MODE_ORGANIZE:
            self._show_organize_mode_ui()
        else:
            self._show_add_new_mode_ui()

    def _show_organize_mode_ui(self):
        """顯示照片整理模式的 UI"""
        # 說明
        desc_label = ctk.CTkLabel(
            self.folder_container,
            text="掃描所有指定資料夾,找出重複檔案,確認後移到待移除項目資料夾",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        desc_label.pack(pady=10)

        # 來源資料夾
        source_frame = ctk.CTkFrame(self.folder_container)
        source_frame.pack(pady=10, padx=10, fill="both", expand=True)

        source_label = ctk.CTkLabel(
            source_frame,
            text="來源資料夾:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        source_label.pack(anchor="w", padx=10, pady=5)

        # 資料夾列表
        self.source_listbox = ctk.CTkTextbox(source_frame, height=200)
        self.source_listbox.pack(padx=10, pady=5, fill="both", expand=True)
        self.source_listbox.configure(state="disabled")

        # 按鈕區域
        button_frame = ctk.CTkFrame(source_frame)
        button_frame.pack(pady=5)

        add_button = ctk.CTkButton(
            button_frame,
            text="新增資料夾",
            command=self._add_source_folder
        )
        add_button.pack(side="left", padx=5)

        clear_button = ctk.CTkButton(
            button_frame,
            text="清除全部",
            command=self._clear_source_folders
        )
        clear_button.pack(side="left", padx=5)

    def _show_add_new_mode_ui(self):
        """顯示照片新增模式的 UI"""
        # 說明
        desc_label = ctk.CTkLabel(
            self.folder_container,
            text="比對新照片資料夾與硬碟資料夾,找到重複後將新照片資料夾裡的重複檔案移到待移除項目資料夾",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        desc_label.pack(pady=10)

        # 新照片資料夾
        new_frame = ctk.CTkFrame(self.folder_container)
        new_frame.pack(pady=10, padx=10, fill="x")

        new_label = ctk.CTkLabel(
            new_frame,
            text="新照片資料夾:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        new_label.pack(anchor="w", padx=10, pady=5)

        new_folder_frame = ctk.CTkFrame(new_frame)
        new_folder_frame.pack(padx=10, pady=5, fill="x")

        self.new_folder_entry = ctk.CTkEntry(new_folder_frame, placeholder_text="尚未選擇")
        self.new_folder_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.new_folder_entry.configure(state="disabled")

        select_new_button = ctk.CTkButton(
            new_folder_frame,
            text="選擇",
            command=self._select_new_folder,
            width=80
        )
        select_new_button.pack(side="left", padx=5)

        # 硬碟資料夾
        disk_frame = ctk.CTkFrame(self.folder_container)
        disk_frame.pack(pady=10, padx=10, fill="both", expand=True)

        disk_label = ctk.CTkLabel(
            disk_frame,
            text="硬碟資料夾:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        disk_label.pack(anchor="w", padx=10, pady=5)

        # 資料夾列表
        self.disk_listbox = ctk.CTkTextbox(disk_frame, height=150)
        self.disk_listbox.pack(padx=10, pady=5, fill="both", expand=True)
        self.disk_listbox.configure(state="disabled")

        # 按鈕區域
        button_frame = ctk.CTkFrame(disk_frame)
        button_frame.pack(pady=5)

        add_disk_button = ctk.CTkButton(
            button_frame,
            text="新增資料夾",
            command=self._add_disk_folder
        )
        add_disk_button.pack(side="left", padx=5)

        clear_disk_button = ctk.CTkButton(
            button_frame,
            text="清除全部",
            command=self._clear_disk_folders
        )
        clear_disk_button.pack(side="left", padx=5)

    # === 照片整理模式的資料夾操作 ===

    def _add_source_folder(self):
        """新增來源資料夾"""
        folder = filedialog.askdirectory(title="選擇來源資料夾")
        if folder:
            self.source_folders.append(folder)
            self._update_source_listbox()

    def _clear_source_folders(self):
        """清除所有來源資料夾"""
        self.source_folders = []
        self._update_source_listbox()

    def _update_source_listbox(self):
        """更新來源資料夾列表顯示"""
        self.source_listbox.configure(state="normal")
        self.source_listbox.delete("1.0", "end")
        for folder in self.source_folders:
            self.source_listbox.insert("end", folder + "\n")
        self.source_listbox.configure(state="disabled")

    # === 照片新增模式的資料夾操作 ===

    def _select_new_folder(self):
        """選擇新照片資料夾"""
        folder = filedialog.askdirectory(title="選擇新照片資料夾")
        if folder:
            self.new_folder = folder
            self.new_folder_entry.configure(state="normal")
            self.new_folder_entry.delete(0, "end")
            self.new_folder_entry.insert(0, folder)
            self.new_folder_entry.configure(state="disabled")

    def _add_disk_folder(self):
        """新增硬碟資料夾"""
        folder = filedialog.askdirectory(title="選擇硬碟資料夾")
        if folder:
            self.disk_folders.append(folder)
            self._update_disk_listbox()

    def _clear_disk_folders(self):
        """清除所有硬碟資料夾"""
        self.disk_folders = []
        self._update_disk_listbox()

    def _update_disk_listbox(self):
        """更新硬碟資料夾列表顯示"""
        self.disk_listbox.configure(state="normal")
        self.disk_listbox.delete("1.0", "end")
        for folder in self.disk_folders:
            self.disk_listbox.insert("end", folder + "\n")
        self.disk_listbox.configure(state="disabled")

    # === 開始掃描 ===

    def _on_start_clicked(self):
        """開始掃描按鈕點擊"""
        mode = self.current_mode.get()

        if mode == MODE_ORGANIZE:
            # 檢查來源資料夾
            is_valid, error_msg = check_folders_validity(self.source_folders)
            if not is_valid:
                messagebox.showerror("錯誤", error_msg)
                return

            # 呼叫回呼函數
            if hasattr(self, 'on_start_organize'):
                self.on_start_organize(self.source_folders)

        else:  # MODE_ADD_NEW
            # 檢查新照片資料夾
            if not self.new_folder:
                messagebox.showerror("錯誤", "請選擇新照片資料夾")
                return

            # 檢查硬碟資料夾,以及與新照片資料夾的關係
            is_valid, error_msg = check_add_new_folders(self.new_folder, self.disk_folders)
            if not is_valid:
                messagebox.showerror("錯誤", error_msg)
                return

            # 呼叫回呼函數
            if hasattr(self, 'on_start_add_new'):
                self.on_start_add_new(self.new_folder, self.disk_folders)

    def set_start_organize_callback(self, callback: Callable):
        """設定照片整理模式開始掃描的回呼函數"""
        self.on_start_organize = callback

    def set_start_add_new_callback(self, callback: Callable):
        """設定照片新增模式開始掃描的回呼函數"""
        self.on_start_add_new = callback

    # === 快取管理 ===

    def _on_resume_clicked(self):
        """繼續上次未完成的處理按鈕點擊"""
        if hasattr(self, 'on_resume_progress'):
            self.on_resume_progress()

    def _on_clear_cache_clicked(self):
        """清除快取按鈕點擊"""
        result = messagebox.askyesno(
            "確認",
            "確定要清除所有快取嗎？\n\n這將刪除:\n• 檔案雜湊快取\n• 未完成的確認進度\n• 未完成的移動操作"
        )
        if result:
            if hasattr(self, 'on_clear_cache'):
                self.on_clear_cache()
            self._update_cache_buttons()

    def _update_cache_buttons(self):
        """更新快取按鈕的啟用/禁用狀態"""
        if hasattr(self, 'on_check_cache'):
            has_progress, mode = self.on_check_cache()
            if has_progress:
                if mode:
                    self.resume_button.configure(
                        state="normal",
                        text=f"📂 繼續上次未完成的處理 ({mode})"
                    )
                else:
                    self.resume_button.configure(
                        state="normal",
                        text="📂 繼續上次未完成的處理"
                    )
            else:
                self.resume_button.configure(
                    state="disabled",
                    text="📂 繼續上次未完成的處理 (無進度)"
                )

    def set_resume_progress_callback(self, callback: Callable):
        """設定繼續進度的回呼函數"""
        self.on_resume_progress = callback

    def set_clear_cache_callback(self, callback: Callable):
        """設定清除快取的回呼函數"""
        self.on_clear_cache = callback

    def set_check_cache_callback(self, callback: Callable):
        """設定檢查快取的回呼函數"""
        self.on_check_cache = callback

    def update_cache_buttons(self):
        """供外部呼叫以更新快取按鈕狀態"""
        self._update_cache_buttons()
