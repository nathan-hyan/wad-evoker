# Roadmap

## What's Implemented

- [x] Import `.wad`, `.pk3`, `.zip`
- [x] Drag & drop onto window
- [x] `.txt` sidecar metadata parsing
- [x] SQLite library with full CRUD
- [x] Tag chips (add / remove)
- [x] Last Played / Recent bar
- [x] Configurable source port binary (Settings dialog)
- [x] Launch with `-file` param passed to binary
- [x] Search (title, author, tags)
- [x] Delete from library (file on disk preserved)
- [x] **TITLEPIC extraction** — `titlepic.py` extracts via `omgifol` for `.wad`; for `.pk3` tries direct PNG/JPG, raw Doom graphic lump, then embedded `.wad`. Cached as PNG under `titlepics/`. Displayed as background on Recent cards and alongside metadata in the detail panel. Lazy extraction on first select for pre-existing library entries.
- [x] **Map list display** — `maplist.py` uses `omgifol` to enumerate all map marker lumps (`MAP##` / `E#M#`) from the WAD. If a `MAPINFO`, `ZMAPINFO`, or `UMAPINFO` lump is present, it is parsed to produce `MAP01: Level Name` formatted lines; otherwise plain map names are used. The result is stored as a newline-separated `map_list` TEXT column in the DB. In the detail panel a `MapListWidget` (full-width scrollable `QTextEdit`, max 200 px tall) is rendered below the Description section and is hidden automatically when no map data is available. Lazy extraction runs on WAD select for pre-existing library entries (mirrors titlepic pattern).
- [x] **Edit WAD dialog** — `WadEditDialog` allows editing title/author/year/game/description, changing the WAD file path (with a Browse picker), and editing `map_list`. Game uses a fixed dropdown (Doom/Doom 2/TNT/Plutonia). Includes a collapsible side-by-side sidecar `.txt` preview with a manual file picker; preview decoding auto-detects common encodings (notably CP437/CP1252).
- [x] **DEH Support** — WADs with `.deh` sidecar files now show a `[DEH]` badge in the library list and in the detail panel (below the title). On launch, if DEH files are present a modal dialog appears with checkboxes listing each `.deh` file (all enabled by default) so the user can choose which patches to apply. The source port is invoked with `-deh <file>` for each selected file.
- [x] **Auto-update** — `updater.py` checks `https://api.github.com/repos/exequiel-mleziva/wad-evoker/releases/latest` on boot (2 s delay, background `QThread`). If a newer tag exists, user is prompted to install; download replaces app files in-place and `os.execv` restarts. Settings dialog exposes a **Check for Updates** button with inline status feedback and an **Update Now** button.

---

## Planned / Nice-to-Haves

- [x] **Multiple named source port profiles** — `sourceport.py` supports multiple profiles stored as `[sourceport_N]` sections in `config.ini` with full CRUD. The active profile persists across sessions via `[sourceport] active`. Legacy single-binary configs are auto-migrated on first load. Settings dialog provides a profile list with add/edit/delete. A `QComboBox` in the status bar (bottom-right) shows the active profile and allows switching. Launch uses the active profile's binary.
- [x] **Time played tracking** — `play_duration_seconds INTEGER DEFAULT 0` in `wads` table. A `ProcessWatcher` (`QThread`) monitors each launched subprocess; on exit it adds the elapsed seconds to the cumulative total and updates `last_played`. Re-launching a WAD while it's already running is blocked. Displayed as a `TIME PLAYED` meta row in the detail panel (e.g. `2h 34m`).
- [ ] **Screenshot support** — store screenshot paths, display in detail panel
- [ ] **Stats** — similar to DoomLauncher (https://github.com/nstlaurent/DoomLauncher): kills, deaths, secrets per session
- [ ] **IWAD selection** — let user specify the base IWAD (`doom2.wad`, `doom.wad`, etc.) passed via `-iwad`
- [x] **Per-WAD source port binding** — `sourceport_profile_id INTEGER` column in the `wads` table (nullable, NULL = use active). Configurable via a `QComboBox` in the Edit dialog ("Default (use active)" + all profiles). A `SOURCE PORT` meta row in the detail panel shows the override name (hidden when default). On launch, the profile ID is resolved to a binary and passed as `binary_override`; if the profile was deleted, falls back to the active profile silently.
- [x] **Extra args per WAD** — `extra_args TEXT` column in the `wads` table. Editable via a free-text `QLineEdit` in the Edit dialog (launch options section, placeholder: `e.g. -skill 4 -warp 1`). Parsed at launch time via `shlex.split()` (with `.split()` fallback) and appended to the source port command line.
- [x] **Finished WADs** — mark WADs as finished via right-click context menu. Finished WADs show a `[DONE]` badge in the library list. Configurable sorting (separator/bottom/in-place) and optional hiding from the Recent bar. Settings in ⚙ Settings → Library.
- [x] **Context menu** — right-click on library list items exposes Play, Edit, Mark as Finished/Unfinished, and Remove from Library actions.
- [ ] **Sort / filter** — sort library by title, date added, last played; filter by tag
- [ ] **Packaging** — `pyproject.toml`, `.desktop` file for Linux app launcher integration, optional PyInstaller bundle
- [x] **Multi-WAD support** — ZIP imports with multiple WADs produce a single library entry. The WAD matching the zip name is auto-selected as primary; when none matches a side-by-side picker dialog (WAD list + .txt readme) lets the user choose. Secondary WADs are stored in the `extra_wads` DB column. On launch, extra WADs appear in the same `FilesLaunchDialog` checklist as DEH files and are appended to the `-file` argument.
