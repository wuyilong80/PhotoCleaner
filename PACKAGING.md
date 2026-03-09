# 打包說明

本文件說明如何使用 PyInstaller 將 Photo Deduplicator 打包成 macOS 應用程式。

## 前置準備

### 安裝 PyInstaller

```bash
pip install pyinstaller
```

### 確保所有相依套件已安裝

```bash
pip install -r requirements.txt
```

## 打包步驟

### Intel Mac

在 Intel Mac 上執行以下命令:

```bash
pyinstaller --name "PhotoDeduplicator" \
    --windowed \
    --onefile \
    --icon=icon.icns \
    --add-data "src:src" \
    main.py
```

如果沒有圖示檔案,可以省略 `--icon` 參數:

```bash
pyinstaller --name "PhotoDeduplicator" \
    --windowed \
    --onefile \
    --add-data "src:src" \
    main.py
```

### Apple Silicon Mac

在 Apple Silicon Mac 上執行相同的命令:

```bash
pyinstaller --name "PhotoDeduplicator" \
    --windowed \
    --onefile \
    --add-data "src:src" \
    main.py
```

## 輸出位置

打包完成後,應用程式會在以下位置:

```
dist/PhotoDeduplicator.app
```

## 常見問題

### 1. 缺少模組錯誤

如果執行時出現缺少模組的錯誤,可以使用 `--hidden-import` 參數:

```bash
pyinstaller --name "PhotoDeduplicator" \
    --windowed \
    --onefile \
    --add-data "src:src" \
    --hidden-import PIL \
    --hidden-import pillow_heif \
    main.py
```

### 2. 應用程式太大

如果希望減小應用程式大小,可以不使用 `--onefile`,改用 `--onedir`:

```bash
pyinstaller --name "PhotoDeduplicator" \
    --windowed \
    --onedir \
    --add-data "src:src" \
    main.py
```

這樣會產生一個資料夾,包含所有必要的檔案。

### 3. 權限問題

打包後的應用程式第一次執行時,macOS 可能會顯示安全警告。使用者需要:

1. 右鍵點擊應用程式
2. 選擇「開啟」
3. 在對話框中點擊「開啟」

### 4. 資料夾存取權限

應用程式需要存取檔案系統,首次使用時 macOS 可能會要求授權。

## 進階選項

### 自訂圖示

如果要使用自訂圖示,需要準備 `.icns` 格式的圖示檔案:

1. 準備一個 1024x1024 的 PNG 圖片
2. 使用 macOS 的 `sips` 和 `iconutil` 工具轉換:

```bash
# 建立 iconset 資料夾
mkdir MyIcon.iconset

# 產生不同尺寸的圖示
sips -z 16 16     icon.png --out MyIcon.iconset/icon_16x16.png
sips -z 32 32     icon.png --out MyIcon.iconset/icon_16x16@2x.png
sips -z 32 32     icon.png --out MyIcon.iconset/icon_32x32.png
sips -z 64 64     icon.png --out MyIcon.iconset/icon_32x32@2x.png
sips -z 128 128   icon.png --out MyIcon.iconset/icon_128x128.png
sips -z 256 256   icon.png --out MyIcon.iconset/icon_128x128@2x.png
sips -z 256 256   icon.png --out MyIcon.iconset/icon_256x256.png
sips -z 512 512   icon.png --out MyIcon.iconset/icon_256x256@2x.png
sips -z 512 512   icon.png --out MyIcon.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out MyIcon.iconset/icon_512x512@2x.png

# 轉換為 icns
iconutil -c icns MyIcon.iconset
```

### 簽署應用程式 (選用)

如果要發布給其他人使用,建議使用 Apple Developer 證書簽署:

```bash
codesign --force --deep --sign "Developer ID Application: Your Name" \
    dist/PhotoDeduplicator.app
```

### 建立 DMG 安裝檔 (選用)

使用 `create-dmg` 工具建立 DMG:

```bash
# 安裝 create-dmg
brew install create-dmg

# 建立 DMG
create-dmg \
    --volname "PhotoDeduplicator" \
    --window-pos 200 120 \
    --window-size 600 300 \
    --icon-size 100 \
    --app-drop-link 425 120 \
    "PhotoDeduplicator.dmg" \
    "dist/PhotoDeduplicator.app"
```

## 測試

打包完成後,請測試以下功能:

1. ✓ 應用程式可以正常啟動
2. ✓ 可以選擇資料夾
3. ✓ 掃描功能正常
4. ✓ 可以顯示縮圖 (包含 HEIC 格式)
5. ✓ 可以移動/刪除檔案
6. ✓ 快取功能正常

## 版本管理

建議在每次打包時記錄版本資訊:

```bash
# 建立 version.txt
echo "1.0.0" > version.txt

# 打包時包含版本資訊
pyinstaller --name "PhotoDeduplicator-v1.0.0" \
    --windowed \
    --onefile \
    --add-data "src:src" \
    --add-data "version.txt:." \
    main.py
```
