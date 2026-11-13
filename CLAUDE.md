# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Photo Deduplicator: a macOS desktop app (CustomTkinter GUI) that finds duplicate photos/videos by SHA-256 content hash, ignoring filenames. All UI strings, comments, docstrings, and output folder names are in Traditional Chinese; keep new code consistent with that.

## Commands

```bash
./run.sh                                   # Run the app (hardcoded to /opt/homebrew/bin/python3.11)
python3 main.py                            # Run with whatever Python is on PATH
pip3 install -r requirements.txt           # Install dependencies
```

- System Python often has Tk version problems; the recommended setup is Homebrew `python@3.11` + `python-tk@3.11`.
- `main.py` calls `check_and_install_packages()` at import time and will `pip install` customtkinter / pillow / pillow-heif if they are missing. It does **not** check `opencv-python`, which `confirmation_window.py` imports lazily for video thumbnails.
- Packaging (see PACKAGING.md): `pyinstaller --name "PhotoDeduplicator" --windowed --onefile --add-data "src:src" main.py` → `dist/PhotoDeduplicator.app`.
- Tests use pytest (not in `requirements.txt`; install with `pip3 install pytest`). Run from the repo root with `python3 -m pytest` so `src` is importable; single test: `python3 -m pytest tests/test_file_utils.py::test_new_folder_inside_disk_folder_is_rejected`. Tests cover only pure functions in `src/utils/`; nothing imports the GUI.
- No linter or formatter is configured.

## Architecture

`main.py` holds `PhotoDeduplicatorApp`, the controller. GUI classes in `src/gui/` don't import core logic; `MainWindow` exposes `set_*_callback()` setters that the app wires to its own methods. Core work (scan, move, delete) runs on daemon `threading.Thread`s, which create `ProgressDialog`s and call `messagebox` directly from the background thread.

### Two modes (`MODE_ORGANIZE` / `MODE_ADD_NEW` in `src/utils/constants.py`)

The mode constants are Chinese strings and are also used as keys in the SQLite `confirmation_progress` table.

1. **Organize (照片整理)**: scan N source folders → `DeduplicateFinder.find_duplicates` groups files by hash → `ConfirmationWindow` steps through groups one at a time; the user must keep at least one file and remove at least one per group → selected files are **moved** (not deleted) to `待移除項目_YYYYMMDD`.
2. **Add new (照片新增)**: scan one "new photos" folder plus N "disk" folders → `find_new_duplicates` returns files in the new folder whose hash exists on disk → one confirm dialog (`AddNewModeResultDialog`) → files are moved to `待移除項目_YYYYMMDD` via the same `_move_files_to_removed` path as Organize mode. Nothing in the app deletes photos outright. This mode has no per-group confirmation and no progress resume. Folder rules live in `check_add_new_folders`: the new folder may sit inside a disk folder (the disk scan passes `exclude_folders=[new_folder]` to `FileScanner.scan_folders`, which skips that subtree), but it must not equal a disk folder and no disk folder may sit inside it. Otherwise the same file is scanned as both "new" and "disk", matches its own hash, and gets removed.

### Output folder placement (`src/utils/file_utils.py`)

`get_output_folder_path` sends files under `/Volumes/<name>/...` to `/Volumes/<name>/<folder>`; everything else goes to `~/Desktop/<folder>`. Inside that folder, moved files keep their original directory structure (`get_mirrored_dest_path`: `/Volumes/HDD/a/IMG.jpg` → `/Volumes/HDD/待移除項目_YYYYMMDD/a/IMG.jpg`; local paths keep the full absolute path under the Desktop folder). Every move goes through `FileOperationManager._move_without_overwrite`, which adds a `_1`, `_2`… suffix rather than overwrite an existing file (`shutil.move` silently replaces on macOS). If hashing fails, `FileScanner` treats the file as corrupted, and `FileOperationManager.move_corrupted_file` moves it to `損壞檔案_YYYYMMDD` along with an `.error.txt` log.

### Persistence: `CacheManager` (`src/core/cache.py`)

A single SQLite DB at `~/.photo_dedup_cache.db` (`CACHE_DB_PATH`). Each method opens and closes its own connection. It has three tables:
- `file_cache`: hash cache keyed by path, valid only while `file_size` and `modified_time` both match.
- `confirmation_progress`: Organize-mode review state, auto-saved on every checkbox change and on window close. The `duplicate_groups` column holds JSON in two shapes: the current one is a dict `{duplicate_groups, completed_groups, selected_files_map}`, and a legacy one is a list. `_resume_organize_progress` in `main.py` handles both. JSON turns the integer keys of `selected_files_map` into strings.
- `pending_moves`: a write-ahead list for Organize-mode moves. It is written before moving and each row is marked complete as its file moves. On startup, `_check_pending_moves` offers to resume an interrupted batch.

"Clear cache" deletes the DB file and rebuilds `CacheManager` and `FileOperationManager`.

### Scanning rules

`FileScanner._collect_files` recurses with `os.scandir` and skips hidden entries and symlinks. Extensions are filtered by `SUPPORTED_EXTENSIONS` (jpg/jpeg/heic/png/mov/mp4/avi). Hashes are computed in 4 MB chunks. `check_folders_validity` rejects duplicate or nested source folders.

### ConfirmationWindow keyboard handling

Shortcuts are registered with `bind_all` (←/→, Enter, Space, A/D, and 1–9 to toggle a file), so they are global to the Tk app. `_unbind_shortcuts()` must run on every exit path, or the handlers leak to other windows.
