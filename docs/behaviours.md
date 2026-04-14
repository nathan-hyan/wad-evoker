# Key Behaviours

## Import flow

1. User clicks **＋ Add WAD** or drops a file onto the window
2. `wad_importer.import_file(path)` is called
3. If `.zip`: extracted to a temp dir, all `.wad`/`.pk3` files inside are found
4. A named subfolder `wads/<zip_basename>/` is created (deduplicated with `_1`, `_2` suffixes). All WADs from the same ZIP share one subfolder (they're one release)
5. All `.txt` and `.deh` sidecar files from the ZIP are copied into the entry subfolder
6. Each WAD is copied into the entry subfolder; its `.txt` sidecar (if found) is parsed for metadata
   - For single `.wad`/`.pk3` imports: subfolder is `wads/<filename_basename>/`, only matching-name sidecars are copied
7. `db.add_wad(...)` is called — silently skips if filepath already exists (UNIQUE constraint)
8. Library list and Recent bar are refreshed

---

## .txt parser (`wad_importer.parse_txt`)

- Parses idgames-archive-format `.txt` files (key `:` value lines)
- Field map: `title`, `author`, `description`, `year`, `game`, `number of levels / map count / levels released → map_count`
- After copy, `maplist.extract_maps(dest)` is called and the result stored as `map_list` (newline-separated string)
- Falls back to `title_from_filename()` (underscore/dash → spaces, title-cased) if no title found
- Continuation lines (indented or non-key lines after a key) are appended to the previous value

---

## Launch flow

1. User selects a WAD and clicks **▶ LAUNCH**
2. **Re-launch guard**: if a `ProcessWatcher` is already active for this WAD ID, an info dialog is shown and launch is aborted
3. `wad_importer.find_deh_files(filepath)` checks for `.deh` files in the entry subfolder
4. If DEH/extra-WAD files exist **and** `wad.skip_files_prompt` is falsy: `FilesLaunchDialog` is shown — a modal with one `StyledCheckBox` per file (all checked by default) plus a "Don't ask again" option. User can deselect files or cancel entirely. If "Don't ask again" is checked, `db.update_skip_files_prompt(wad_id, True)` is saved immediately.
5. If `skip_files_prompt` is already set, all DEH/extra-WAD files are used automatically without showing the dialog.
6. **Per-WAD extra args**: if the WAD has `extra_args` set (free-text string), it is parsed via `shlex.split()` (with fallback to `.split()` on malformed quotes)
7. **Auto-warp**: if the WAD has `auto_warp` enabled, `-warp` args are injected into the command:
   - If `warp_target` is set (user override), that map name is converted to `-warp` args via `maplist.map_to_warp_args()`
   - If `warp_target` is empty, the first map lump is auto-detected from the WAD via `maplist.get_warp_info()`
   - Skipped if `-warp` is already present in the per-WAD extra args
   - Supports `MAPxx` (→ `-warp N`) and `ExMy` (→ `-warp E M`) formats; non-standard names are skipped
8. **Per-WAD source port**: if the WAD has `sourceport_profile_id` set, the corresponding profile's binary is looked up. If the profile was deleted, falls back to the active profile silently.
9. `sourceport.launch_wad(filepath, deh_files=[...], extra_args=[...], binary_override=...)` is called
10. Runs: `subprocess.Popen([binary, "-file", wad_filepath, ...extra_wads, -deh ..., ...extra_args])`
11. On success: a `ProcessWatcher` (`QThread`) is spawned to wait for the process to exit
12. **On process exit** (`_on_process_finished`): `db.update_last_played(wad_id)` and `db.add_play_duration(wad_id, elapsed_seconds)` are called, the Recent bar refreshes, and if the WAD is still selected in the detail panel, it is re-rendered with updated time
13. On failure: `QMessageBox.warning` shown with the error

The `skip_files_prompt` flag can be reset per-entry via the **✎ EDIT** dialog ("Skip files selection dialog on launch" checkbox).

Extra args, auto-warp, and per-WAD source port are also configurable in the **✎ EDIT** dialog (launch options section below the form).

### Auto-warp smart default

At import time, `maplist.get_warp_info(filepath)` analyses the WAD/PK3:
- If the file contains **no** MAPINFO/ZMAPINFO/UMAPINFO lump, **and** the first map is not `MAP01` or `E1M1`, `auto_warp` is set to `true` automatically.
- WADs with any MAPINFO variant, or that start at `MAP01`/`E1M1`, default to `auto_warp = false`.
- Existing WADs in the library are not affected (default `false`).

---

## Edit metadata flow

1. User selects a WAD and clicks **✎ EDIT** (left of the Launch button)
2. `WadDetailPanel` emits `edit_requested(wad_id)`
3. `MainWindow._on_edit` opens `WadEditDialog(wad_id)`
4. On **Save**, `db.update_wad(...)` updates the editable columns in the `wads` table
5. Library list is refreshed and the detail panel re-renders the updated WAD
6. If `titlepic_path` or `map_list` are cleared, the app re-extracts them from the WAD on disk

---

## Source port config

- Multiple named profiles stored in `~/.config/wad-evoker/config.ini` as `[sourceport_N]` sections (name + binary)
- Active profile persisted via `[sourceport] active`; legacy single-binary configs auto-migrated on first load
- Manageable via **⚙ Settings → Source Ports** (add/edit/delete) — no restart needed
- A `QComboBox` in the status bar (bottom-right) shows the active profile and allows switching
- Settings dialog validates binary path live: checks `os.path.isfile` + `os.access(X_OK)`
- Launch uses the active profile's binary by default; individual WADs can override this via a per-WAD source port binding (set in the Edit dialog, stored as `sourceport_profile_id` in the DB)

---

## Tags

- Stored in `tags` table, linked by `wad_id`
- UI: chip-style widgets with × remove button, plus a text input to add new tags
- `TagsWidget` emits `tags_changed(list)` signal; `MainWindow` diffs against DB and syncs

---

## Search

- `db.search_wads(query)` does a LIKE match across `wads.title`, `wads.author`, and `tags.tag`
- Live — fires on every keystroke via `QLineEdit.textChanged`

---

## Finished WADs

- Any WAD can be marked as finished via right-click → **Mark as Finished** in the library list
- A `[DONE]` chip badge (green) appears next to the title in the WAD list (can be disabled via `show_finished_badge` setting)
- Toggling back is done via right-click → **Mark as Unfinished**
- `db.set_finished(wad_id, bool)` stores the state as `finished INTEGER DEFAULT 0` in the `wads` table
- Library list sorting is controlled by the `finished_sort_mode` setting in `config.ini [library]`:
  - `separator` (default): unfinished WADs first, then a "FINISHED" separator row, then finished WADs
  - `bottom`: finished WADs moved to end, no separator
  - `none`: no reordering, WADs stay in alphabetical position
- The Recent bar can optionally hide finished WADs (`hide_finished_from_recent` setting, default `true`)
- Both settings are configurable in **⚙ Settings → Library**

---

## Context Menu (WAD list)

Right-clicking a WAD in the library list shows:

1. **▶ Play** — launches the WAD (same as detail panel LAUNCH button)
2. **✎ Edit** — opens the edit dialog (same as detail panel EDIT button)
3. *(separator)*
4. **✓ Mark as Finished** / **Mark as Unfinished** — toggles the finished state
5. *(separator)*
6. **Remove from Library** — triggers the delete flow (same as detail panel Remove button)
