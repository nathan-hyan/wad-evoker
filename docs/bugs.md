# Known Bugs & Fixes

## MAPINFO `lookup` keyword (fixed)

ZDoom-format MAPINFO files use `map MAP01 lookup "HUSTR_1"` to reference names from the `LANGUAGE` lump. The original quoted-name regex (`map (\w+) "([^"]+)"`) did not account for the `lookup` keyword, so those lines were never matched. The unquoted fallback then matched them and captured the literal word `lookup` as the display name — causing every map to appear as `"lookup"` in the UI.

**Fix** (`maplist.py` → `_parse_mapinfo_text`):

- Quoted regex updated to `map (\w+) (?:lookup )?"([^"]+)"` — now captures the quoted key regardless of whether `lookup` is present.
- Unquoted fallback guards against `name.lower() == "lookup"` to prevent the word leaking through if somehow reached.

**Library migration note**:

- Older DB entries may have stored `map_list` lines where every map name was literally `lookup`. On WAD selection, `MainWindow._on_wad_selected` now refreshes the stored `map_list` if it is empty or contains the substring `lookup`.

---

## Detail panel — MAPS meta row & map list layout (fixed)

The left metadata column had a redundant `MAPS` row (showing `—`) alongside a 180 px-wide `MapListWidget` squeezed between the metadata and the TITLEPIC image. Map names with long titles were truncated and unreadable.

**Fix** (`ui/wad_detail.py`):

- Removed the `MAPS` meta row from `_build_ui` and its corresponding assignment in `show_wad`.
- Removed `setFixedWidth(180)` from `MapListWidget` so it stretches to full panel width.
- Moved `MapListWidget` out of the `meta_and_pic` `QHBoxLayout` and into the main `detail_layout` directly below the Description section.
- Increased `MapListWidget` max height from 125 → 200 px.

---

## Delete WAD — hard-delete option (fixed)

When deleting a WAD entry, users could only remove it from the library database — the `.wad`/`.pk3` file remained on disk with no option to delete it. This caused orphaned files to accumulate in `~/.config/wad-evoker/wads/`.

**Fix** (`ui/main_window.py` → `MainWindow._on_delete`):

- Replaced simple Yes/No confirmation with a 3-option dialog:
  - **Cancel** — abort the operation
  - **Remove from Library** — delete DB entry only (original behavior)
  - **Remove + Delete File** — delete DB entry and also delete the file from disk
- **Safety guard**: Hard-delete is only allowed if the WAD's `filepath` is inside the app-managed library folder (`wad_importer.WAD_DIR`). Uses `os.path.commonpath()` to verify the file is a child of the managed directory.
- If the user requests hard-delete but the file is outside the managed folder, a warning dialog is shown and the operation falls back to library-only removal.
- Error handling: If `os.remove()` fails (permissions, file in use, etc.), a warning dialog is shown with the error message. The DB entry is still removed.
- Status bar feedback differentiates between "WAD removed from library" and "WAD removed and file deleted."

---

## Auto-updater progress feedback (fixed)

When users accepted an update, the only feedback was a "Downloading Update" message in the status bar. There was no visual indication of download progress or installation status, making it unclear whether the update was working or stalled.

**Fix** (`updater.py` + `ui/update_progress_dialog.py` + `ui/main_window.py`):

- Created `UpdateProgressDialog` — a modal dialog with progress bar, status label, and download size display
- Modified `UpdateDownloadWorker` to emit `progress(downloaded, total)` and `status_changed(message)` signals during download
- Download now reads in chunks (8KB) and reports progress after each chunk
- Progress bar shows percentage and MB downloaded/total
- Status messages update through phases: "Downloading update...", "Extracting update...", "Installing update...", "Update complete! Restarting..."
- Dialog uses indeterminate progress mode during extraction/installation phases
- Styled to match the app's dark terminal aesthetic with blood-red progress bar gradient
- On failure, dialog closes and error is shown via `QMessageBox`

---

## Sidecar .txt not imported alongside WAD (fixed)

When importing a `.zip` (or a single `.wad`/`.pk3`), the `.txt` sidecar file was parsed for metadata but never copied to the managed library folder. The temp extraction dir was deleted after import, leaving the WAD in `wads/` with no `.txt` next to it. Opening the Edit dialog and clicking **Show .txt** always showed "No sidecar .txt selected/found."

**Fix** (`wad_importer.py`):

- Every import now creates a named subfolder under `WAD_DIR`: `wads/<zip_basename>/` for ZIP imports, `wads/<wad_basename>/` for single file imports.
- For ZIP imports: all `.txt` and `.deh` files from the entire extracted tree are copied into the entry subfolder before the temp dir is deleted. All WADs from the same ZIP share one subfolder (they're one release).
- For single WAD imports: `.txt` and `.deh` files whose name matches the WAD basename are copied from the source directory into the entry subfolder.
- `_unique_dest` (flat WAD_DIR placement) is replaced by `_make_entry_subdir` + `_unique_dest_in_dir`.
- `WadEditDialog._find_sidecar_txt` already looks in `os.path.dirname(wad_filepath)` — with the subfolder layout it now finds the `.txt` correctly.
- Hard-delete (`_on_delete`) was updated to also `os.rmdir` the entry subfolder when it becomes empty after the WAD file is removed.

---

## Stale metadata on drag-and-drop import (fixed)

When a WAD was drag-and-dropped and imported, the detail panel would sometimes display metadata from a previously selected WAD instead of the newly imported one. The TITLEPIC and filename were correct, but title, author, description, and other fields showed cached data from another WAD in the library.

**Root causes**:

1. **Incorrect .txt sidecar fallback** (`wad_importer.py` → `_find_and_parse_txt`):
   - When no matching `.txt` file was found for a WAD, the function had a fallback that grabbed **any** `.txt` file in the same directory
   - This caused WADs without sidecars to inherit metadata from unrelated `.txt` files (e.g., other WADs' sidecars in the same import folder)
   - Result: WADs imported with completely wrong metadata from random `.txt` files

2. **Stale cached data in list widget** (`ui/main_window.py`):
   - `WadListWidget.populate()` stores WAD data in `Qt.ItemDataRole.UserRole` for each list item
   - When `refresh_library()` was called after import, the list was cleared and rebuilt
   - During this rebuild, Qt's selection mechanism could trigger `currentItemChanged` with stale WAD data
   - `_on_wad_selected` received this cached dict and displayed it without verifying against the database
   - The newly imported WAD's ID was never explicitly selected, so the wrong WAD's data persisted in the detail panel

**Fix** (`wad_importer.py` → `_find_and_parse_txt`):

- Removed the fallback loop that grabbed any `.txt` file in the directory
- Now only parses `.txt` files that match the WAD filename (e.g., `mymap.txt` for `mymap.wad`)
- WADs without matching sidecars import with minimal metadata (filename-derived title only), allowing users to fill in details manually

**Fix** (`ui/main_window.py` → `_import_path` and `_on_wad_selected`):

- Track `last_imported_id` during the import loop to identify the most recently imported WAD
- Call `detail_panel.clear()` before `refresh_library()` to prevent stale data from being displayed during the refresh
- After refresh, explicitly select the newly imported WAD by calling `wad_list.select_wad_by_id(last_imported_id)`
- Modified `_on_wad_selected` to **always fetch fresh data from the database** using `db.get_wad_by_id(wad_id)` instead of trusting the cached dict passed from the list widget
- This ensures the detail panel always displays current, accurate metadata regardless of list widget state
