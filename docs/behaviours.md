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

## Re-scan Library

- **⚙ Settings → Library → Re-scan Library** triggers a background re-extraction of all WADs
- `LibraryRescanWorker` (`QThread`) iterates every WAD in the DB:
  - `mapinfo_data`: **always** re-extracted (picks up parser improvements)
  - `map_list`: re-extracted only if empty or contains `"lookup"` placeholders
  - `titlepic_path`: extracted only if currently missing
- A thin progress bar and `N/N` counter update live during the scan
- On completion, a summary shows how many entries were updated (e.g. "Done — updated 12 MAPINFO, 3 map lists, 1 titlepics")
- The library list is automatically refreshed via `parent.refresh_library()`
- WADs whose files no longer exist on disk are silently skipped

---

## Full MAPINFO extraction

- On WAD select, if `mapinfo_data` is empty, `maplist.extract_mapinfo_data(filepath)` is called (lazy, mirrors titlepic/maplist pattern)
- Supports `.wad` (via omgifol lump access) and `.pk3` (zip text files + embedded WADs)
- Lump priority: ZMAPINFO → MAPINFO → UMAPINFO
- Parser is block-aware: tokenizes the text, identifies top-level blocks (`map`, `episode`, `cluster`/`clusterdef`, `skill`, `clearepisodes`, `clearskills`), and parses `key = value` properties within braces
- Extracted data structure (stored as JSON in `mapinfo_data` column):
  - `maps`: per-map properties — title, music, sky, next, secretnext, par time, cluster, levelnum, author
  - `episodes`: list of episode definitions — start_map, name, pic, key
  - `skills`: custom skill definitions — name, key, ammofactor, damagefactor
  - `clusters`: cluster/clusterdef data — flat, music, exittext, entertext
  - `source`: which lump was parsed ("MAPINFO", "ZMAPINFO", or "UMAPINFO")
- UMAPINFO-specific: `levelname` → title, `partime` → par, `nextsecret` → secretnext, `episode` property inside map blocks
- Detail panel displays via `MapInfoWidget`: EPISODES (numbered), SKILLS (bulleted), MAP DETAILS (per-map lines with par, music, sky, flow arrows)
- Sections auto-hide when no relevant data exists

---

## Gameplay Mods

WADs/PK3s that contain no map lumps are detected at import time. A 3-option dialog asks:

1. **Mark as Gameplay Mod** — sets `is_gameplay_mod = 1`, entry appears in the "GAMEPLAY MODS" section
2. **Import as Regular WAD** — imports normally despite having no maps
3. **Cancel** — deletes the just-imported entry and aborts

### Library display

- Gameplay mods are shown in a dedicated section at the **bottom** of the library list (above the "FINISHED" section)
- A "GAMEPLAY MODS" separator row divides them from regular WADs
- An orange `[MOD]` badge chip appears on each entry in the list and in the detail panel badge row
- Gameplay mods are **excluded** from the Recent / Last Played bar
- The flag is toggleable via the "Mark as gameplay mod" checkbox in the **✎ EDIT** dialog

### Launch flow — from a gameplay mod entry

1. User clicks **▶ LAUNCH** on a gameplay mod
2. `GameplayModLaunchDialog` opens with a **searchable list** of all non-mod WADs in the library
3. User picks a PWAD to play alongside, or clicks **Skip (IWAD only)**
4. Command: `[binary] -file <pwad> <gameplay_mod> [pwad_extra_wads] [-deh pwad_dehs] [extra_args]`
5. If no PWAD selected: `[binary] -file <gameplay_mod> [extra_args]`

### Launch flow — attaching a gameplay mod to a regular WAD

1. User clicks **▶ LAUNCH** on a regular WAD
2. If gameplay mods exist in the library **or** the WAD has extra files, `FilesLaunchDialog` appears
3. The dialog includes a "GAMEPLAY MOD" combo box at the top (if gameplay mods exist) listing all gameplay mods + "None"
4. The selected mod's file is appended **after** the primary WAD and extra WADs in the `-file` list (mod overrides actors)
5. "Don't ask again" skips the entire dialog (including mod selection) on future launches

---

## Context Menu (WAD list)

Right-clicking a WAD in the library list shows:

1. **▶ Play** — launches the WAD (same as detail panel LAUNCH button)
2. **✎ Edit** — opens the edit dialog (same as detail panel EDIT button)
3. *(separator)*
4. **✓ Mark as Finished** / **Mark as Unfinished** — toggles the finished state
5. *(separator)*
6. **Remove from Library** — triggers the delete flow (same as detail panel Remove button)
