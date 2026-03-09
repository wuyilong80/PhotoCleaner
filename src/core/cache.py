"""快取管理模組 - 使用 SQLite 儲存檔案雜湊值與處理進度"""
import sqlite3
import os
import json
from pathlib import Path
from datetime import datetime
from ..utils.constants import CACHE_DB_PATH


class CacheManager:
    """快取管理器"""

    def __init__(self, db_path=CACHE_DB_PATH):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """初始化資料庫表格"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 檔案雜湊快取表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_cache (
                file_path TEXT PRIMARY KEY,
                file_size INTEGER NOT NULL,
                modified_time REAL NOT NULL,
                sha256 TEXT NOT NULL,
                last_checked REAL NOT NULL
            )
        ''')

        # 確認進度表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS confirmation_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL,
                current_group INTEGER DEFAULT 0,
                total_groups INTEGER DEFAULT 0,
                duplicate_groups TEXT,
                completed_groups TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        ''')

        # 未完成的移動操作表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_moves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL,
                dest_path TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        ''')

        conn.commit()
        conn.close()

    def get_file_hash(self, file_path, file_size, modified_time):
        """從快取取得檔案雜湊值

        Args:
            file_path: 檔案路徑
            file_size: 檔案大小
            modified_time: 修改時間

        Returns:
            SHA-256 雜湊值,若無快取則返回 None
        """
        # 先檢查檔案是否還存在
        if not os.path.exists(file_path):
            self.remove_file_cache(file_path)
            return None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT sha256 FROM file_cache
            WHERE file_path = ? AND file_size = ? AND modified_time = ?
        ''', (file_path, file_size, modified_time))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def save_file_hash(self, file_path, file_size, modified_time, sha256):
        """儲存檔案雜湊值到快取

        Args:
            file_path: 檔案路徑
            file_size: 檔案大小
            modified_time: 修改時間
            sha256: SHA-256 雜湊值
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().timestamp()

        cursor.execute('''
            INSERT OR REPLACE INTO file_cache
            (file_path, file_size, modified_time, sha256, last_checked)
            VALUES (?, ?, ?, ?, ?)
        ''', (file_path, file_size, modified_time, sha256, now))

        conn.commit()
        conn.close()

    def remove_file_cache(self, file_path):
        """移除不存在的檔案快取"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM file_cache WHERE file_path = ?', (file_path,))

        conn.commit()
        conn.close()

    def cleanup_invalid_cache(self):
        """清理所有無效的快取 (檔案不存在)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT file_path FROM file_cache')
        all_paths = cursor.fetchall()

        removed_count = 0
        for (file_path,) in all_paths:
            if not os.path.exists(file_path):
                cursor.execute('DELETE FROM file_cache WHERE file_path = ?', (file_path,))
                removed_count += 1

        conn.commit()
        conn.close()

        return removed_count

    # === 確認進度相關 ===

    def save_confirmation_progress(self, mode, current_group, total_groups,
                                   duplicate_groups, completed_groups):
        """儲存確認進度

        Args:
            mode: 模式 (照片整理/照片新增)
            current_group: 目前組別
            total_groups: 總組數
            duplicate_groups: 重複組別資料 (list of dicts)
            completed_groups: 已完成的組別索引列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().timestamp()

        # 先清除舊的進度
        cursor.execute('DELETE FROM confirmation_progress WHERE mode = ?', (mode,))

        # 儲存新進度
        cursor.execute('''
            INSERT INTO confirmation_progress
            (mode, current_group, total_groups, duplicate_groups, completed_groups,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (mode, current_group, total_groups,
              json.dumps(duplicate_groups, ensure_ascii=False),
              json.dumps(completed_groups),
              now, now))

        conn.commit()
        conn.close()

    def load_confirmation_progress(self, mode):
        """載入確認進度

        Returns:
            (current_group, total_groups, duplicate_groups, completed_groups) 或 None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT current_group, total_groups, duplicate_groups, completed_groups
            FROM confirmation_progress
            WHERE mode = ?
            ORDER BY updated_at DESC
            LIMIT 1
        ''', (mode,))

        result = cursor.fetchone()
        conn.close()

        if result:
            current_group, total_groups, duplicate_groups_json, completed_groups_json = result
            duplicate_groups = json.loads(duplicate_groups_json)
            completed_groups = json.loads(completed_groups_json)
            return current_group, total_groups, duplicate_groups, completed_groups

        return None

    def clear_confirmation_progress(self, mode):
        """清除確認進度"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM confirmation_progress WHERE mode = ?', (mode,))

        conn.commit()
        conn.close()

    # === 未完成移動操作相關 ===

    def save_pending_moves(self, move_list):
        """儲存待移動清單

        Args:
            move_list: [(source_path, dest_path), ...]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 先清除舊的未完成移動
        cursor.execute('DELETE FROM pending_moves')

        now = datetime.now().timestamp()

        for source_path, dest_path in move_list:
            cursor.execute('''
                INSERT INTO pending_moves
                (source_path, dest_path, completed, created_at, updated_at)
                VALUES (?, ?, 0, ?, ?)
            ''', (source_path, dest_path, now, now))

        conn.commit()
        conn.close()

    def mark_move_completed(self, source_path):
        """標記某個移動操作已完成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().timestamp()

        cursor.execute('''
            UPDATE pending_moves
            SET completed = 1, updated_at = ?
            WHERE source_path = ?
        ''', (now, source_path))

        conn.commit()
        conn.close()

    def get_pending_moves(self):
        """取得所有未完成的移動操作

        Returns:
            [(source_path, dest_path), ...]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT source_path, dest_path
            FROM pending_moves
            WHERE completed = 0
            ORDER BY id
        ''')

        results = cursor.fetchall()
        conn.close()

        return results

    def has_pending_moves(self):
        """檢查是否有未完成的移動操作"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM pending_moves WHERE completed = 0')
        count = cursor.fetchone()[0]

        conn.close()

        return count > 0

    def clear_pending_moves(self):
        """清除所有移動操作記錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM pending_moves')

        conn.commit()
        conn.close()
