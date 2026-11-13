# Photo Deduplicator

macOS 照片去重工具,支援照片整理與照片新增兩種模式。

## 功能特色

- **照片整理模式**: 掃描指定資料夾,找出重複檔案並移至待移除項目資料夾
- **照片新增模式**: 比對新照片與硬碟資料夾,將新照片資料夾中已存在於硬碟的檔案移至待移除項目資料夾 (新照片資料夾可放在硬碟資料夾裡面,掃描硬碟時會自動跳過它;但兩者不可相同,硬碟資料夾也不可放在新照片資料夾裡面)
- 支援格式: JPG、JPEG、HEIC、PNG、MOV、MP4、AVI
- SHA-256 內容比對,與檔名無關
- 智慧快取機制,加速重複掃描
- 自動處理損壞檔案

## 安裝

### 方法 1: 使用 Homebrew Python (推薦)

```bash
# 安裝 Python 3.11
brew install python@3.11

# 安裝 tkinter 支援
brew install python-tk@3.11

# 安裝相依套件
/opt/homebrew/bin/pip3.11 install customtkinter Pillow pillow-heif
```

### 方法 2: 使用系統 Python (可能需要較舊版本的 customtkinter)

```bash
pip3 install -r requirements.txt
```

## 執行

### 使用啟動腳本 (推薦)

```bash
./run.sh
```

### 使用 Python 3.11

```bash
/opt/homebrew/bin/python3.11 main.py
```

### 使用系統 Python

```bash
python3 main.py
```

## 測試

```bash
pip3 install pytest
python3 -m pytest
```

## 打包

### Intel Mac
```bash
pyinstaller --onefile --windowed --name PhotoDeduplicator main.py
```

### Apple Silicon Mac
```bash
pyinstaller --onefile --windowed --name PhotoDeduplicator main.py
```

## 系統需求

- macOS 10.14+
- Python 3.8+
