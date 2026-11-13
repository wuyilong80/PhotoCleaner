"""進度對話框"""
import customtkinter as ctk
from typing import Optional


class ProgressDialog(ctk.CTkToplevel):
    """進度顯示對話框"""

    def __init__(self, parent, title="處理中"):
        super().__init__(parent)

        self.title(title)
        self.geometry("500x200")

        # 禁止關閉
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        # 建立 UI
        self._create_ui()

    def _create_ui(self):
        """建立使用者介面"""
        # 主訊息
        self.message_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=14)
        )
        self.message_label.pack(pady=20, padx=20)

        # 進度條
        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.pack(pady=10, padx=20)
        self.progress_bar.set(0)

        # 詳細資訊
        self.detail_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.detail_label.pack(pady=5, padx=20)

        # 預估剩餘時間
        self.eta_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.eta_label.pack(pady=5, padx=20)

    def update_progress(self, current: int, total: int, message: str = "",
                       detail: str = "", eta_seconds: float = 0):
        """更新進度

        Args:
            current: 當前進度
            total: 總數
            message: 主訊息
            detail: 詳細資訊
            eta_seconds: 預估剩餘秒數
        """
        # 更新進度條
        if total > 0:
            progress = current / total
            self.progress_bar.set(progress)
        else:
            self.progress_bar.set(0)

        # 更新訊息
        if message:
            self.message_label.configure(text=f"{message} ({current}/{total})")

        if detail:
            # 截斷過長的路徑
            if len(detail) > 60:
                detail = "..." + detail[-57:]
            self.detail_label.configure(text=detail)

        # 更新預估時間
        if eta_seconds > 0:
            eta_text = self._format_eta(eta_seconds)
            self.eta_label.configure(text=f"預估剩餘時間: {eta_text}")
        else:
            self.eta_label.configure(text="")

        # 強制更新 UI
        self.update()

    def _format_eta(self, seconds: float) -> str:
        """格式化預估時間"""
        if seconds < 60:
            return f"{int(seconds)} 秒"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes} 分 {secs} 秒"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours} 小時 {minutes} 分"

    def close_dialog(self):
        """關閉對話框"""
        self.destroy()


class AddNewModeResultDialog(ctk.CTkToplevel):
    """照片新增模式結果對話框"""

    def __init__(self, parent, duplicate_count: int, on_confirm_callback):
        super().__init__(parent)

        self.title("找到重複檔案")
        self.geometry("400x200")

        self.duplicate_count = duplicate_count
        self.on_confirm_callback = on_confirm_callback

        self._create_ui()

    def _create_ui(self):
        """建立使用者介面"""
        # 訊息
        message = f"找到 {self.duplicate_count} 個重複檔案\n將從新照片資料夾移到待移除項目資料夾"
        message_label = ctk.CTkLabel(
            self,
            text=message,
            font=ctk.CTkFont(size=16),
            justify="center"
        )
        message_label.pack(pady=30, padx=20)

        # 按鈕
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=20)

        confirm_button = ctk.CTkButton(
            button_frame,
            text="確認移動",
            command=self._on_confirm,
            width=120
        )
        confirm_button.pack(side="left", padx=10)

        cancel_button = ctk.CTkButton(
            button_frame,
            text="取消",
            command=self.destroy,
            width=120
        )
        cancel_button.pack(side="left", padx=10)

    def _on_confirm(self):
        """確認移動"""
        self.on_confirm_callback()
        self.destroy()


class CompletionDialog(ctk.CTkToplevel):
    """完成對話框"""

    def __init__(self, parent, title="完成", message="操作完成"):
        super().__init__(parent)

        self.title(title)
        self.geometry("400x200")

        # 訊息
        message_label = ctk.CTkLabel(
            self,
            text=message,
            font=ctk.CTkFont(size=16),
            justify="center"
        )
        message_label.pack(pady=40, padx=20)

        # 確定按鈕
        ok_button = ctk.CTkButton(
            self,
            text="確定",
            command=self.destroy,
            width=120
        )
        ok_button.pack(pady=20)
