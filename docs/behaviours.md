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
2. `wad_importer.find_deh_files(filepath)` checks for `.deh` files in the entry subfolder
3. If DEH files exist **and** `wad.skip_files_prompt` is falsy: `FilesLaunchDialog` is shown — a modal with one `StyledCheckBox` per file (all checked by default) plus a "Don't ask again" option. User can deselect files or cancel entirely. If "Don't ask again" is checked, `db.update_skip_files_prompt(wad_id, True)` is saved immediately.
4. If `skip_files_prompt` is already set, all DEH files are used automatically without showing the dialog.
5. `sourceport.launch_wad(filepath, deh_files=[...])` is called
6. Runs: `subprocess.Popen([binary, "-file", wad_filepath, "-deh", deh1, "-deh", deh2, ...])`
7. On success: `db.update_last_played(wad_id)` is called, Recent bar refreshes
8. On failure: `QMessageBox.warning` shown with the error

The `skip_files_prompt` flag can be reset per-entry via the **✎ EDIT** dialog ("Skip files selection dialog on launch" checkbox at the bottom of the form).

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

- Stored in `~/.config/wad-evoker/config.ini` under `[sourceport] binary = /path/to/binary`
- Changeable at runtime via **⚙ Settings** — no restart needed
- Settings dialog validates path live: checks `os.path.isfile` + `os.access(X_OK)`
- Currently single binary — designed for easy extension to named profiles

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
- A `[DONE]` chip badge (green) appears next to the title in the WAD list
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
