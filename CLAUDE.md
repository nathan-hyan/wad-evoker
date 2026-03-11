# Wad Evoker — Project Context

A Python + PyQt6 desktop WAD library manager and launcher for classic Doom (1993).
Dark, terminal-aesthetic UI. Linux-native, but cross-platform via PyQt6 (Windows/macOS compatible).

---

## Stack

- **Language**: Python 3.10+
- **GUI**: PyQt6
- **Database**: SQLite via Python's built-in `sqlite3`
- **Config**: `configparser` — INI file at `~/.config/wad-evoker/config.ini`
- **WAD parsing**: `omgifol` 0.5.1 — lump access + Doom graphic decoding (`to_Image("RGBA")`)
- **Image handling**: `Pillow` — RGBA conversion and PNG cache writes

---

## Project Structure

```
wad-evoker/
├── main.py                  # Entry point — boots QApplication, inits DB, shows MainWindow
├── db.py                    # All SQLite logic (CRUD for wads + tags)
├── titlepic.py              # TITLEPIC extraction: WAD (omgifol) + PK3 (zip strategies) → cached PNG
├── maplist.py               # Map list extraction: WAD/PK3 via omgifol, MAPINFO/ZMAPINFO/UMAPINFO parsing
├── wad_importer.py          # File import: .wad, .pk3, .zip extraction + .txt metadata parser
├── sourceport.py            # Source port config (read/write binary path) + subprocess launch
├── version.py               # Single source of truth for __version__ (e.g. "1.0.0")
├── updater.py               # Auto-update: GitHub release check, zip download, file replacement, restart
├── requirements.txt         # PyQt6, omgifol, Pillow
├── README.md
└── ui/
    ├── __init__.py
    ├── main_window.py       # Main window: toolbar, drag-drop, search, splitter layout
    ├── wad_list.py          # Left panel: QListWidget of WADs
    ├── wad_detail.py        # Right panel: metadata display, tags, launch button
    ├── last_played.py       # Top "Recent" horizontal card strip
    └── settings_dialog.py   # Source port binary picker dialog
```

---

## Data Storage

All user data lives under `~/.config/wad-evoker/`:

| Path         | Purpose                                                               |
| ------------ | --------------------------------------------------------------------- |
| `library.db` | SQLite database                                                       |
| `wads/`      | Imported WAD/PK3 files (copied here on import)                        |
| `titlepics/` | Cached TITLEPIC PNGs (md5-named, extracted on import or first select) |
| `config.ini` | Source port binary path                                               |

---

## Database Schema

```sql
CREATE TABLE wads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    filename    TEXT NOT NULL,
    filepath    TEXT NOT NULL UNIQUE,
    author      TEXT,
    description TEXT,
    year        TEXT,
    game        TEXT,
    map_count     TEXT,
    map_list      TEXT,
    titlepic_path TEXT,
    added_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_played   TIMESTAMP
);

CREATE TABLE tags (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    wad_id  INTEGER NOT NULL REFERENCES wads(id) ON DELETE CASCADE,
    tag     TEXT NOT NULL,
    UNIQUE(wad_id, tag)
);
```

---

## Key Behaviours

### Import flow

1. User clicks **＋ Add WAD** or drops a file onto the window
2. `wad_importer.import_file(path)` is called
3. If `.zip`: extracted to a temp dir, all `.wad`/`.pk3` files inside are found
4. Each WAD is copied to `~/.config/wad-evoker/wads/` (deduplicated with `_1`, `_2` suffixes)
5. A `.txt` sidecar file in the same directory is parsed for metadata
6. `db.add_wad(...)` is called — silently skips if filepath already exists (UNIQUE constraint)
7. Library list and Recent bar are refreshed

### .txt parser (`wad_importer.parse_txt`)

- Parses idgames-archive-format `.txt` files (key `:` value lines)
- Field map: `title`, `author`, `description`, `year`, `game`, `number of levels / map count / levels released → map_count`
- After copy, `maplist.extract_maps(dest)` is called and the result stored as `map_list` (newline-separated string)
- Falls back to `title_from_filename()` (underscore/dash → spaces, title-cased) if no title found
- Continuation lines (indented or non-key lines after a key) are appended to the previous value

### Launch flow

1. User selects a WAD and clicks **▶ LAUNCH**
2. `sourceport.launch_wad(filepath)` is called
3. Runs: `subprocess.Popen([binary, "-file", wad_filepath])`
4. On success: `db.update_last_played(wad_id)` is called, Recent bar refreshes
5. On failure: `QMessageBox.warning` shown with the error

### Source port config

- Stored in `~/.config/wad-evoker/config.ini` under `[sourceport] binary = /path/to/binary`
- Changeable at runtime via **⚙ Settings** — no restart needed
- Settings dialog validates path live: checks `os.path.isfile` + `os.access(X_OK)`
- Currently single binary — designed for easy extension to named profiles

### Tags

- Stored in `tags` table, linked by `wad_id`
- UI: chip-style widgets with × remove button, plus a text input to add new tags
- `TagsWidget` emits `tags_changed(list)` signal; `MainWindow` diffs against DB and syncs

### Search

- `db.search_wads(query)` does a LIKE match across `wads.title`, `wads.author`, and `tags.tag`
- Live — fires on every keystroke via `QLineEdit.textChanged`

---

## UI / Styling

- **Aesthetic**: Dark terminal / Doom-flavored. Blood red (`#cc2200`) accents, near-black backgrounds, `Courier New` monospace throughout
- **All styles are inline QSS** (Qt StyleSheets) applied per-widget via `setStyleSheet()`
- No external style files or asset dependencies
- Key color tokens (not extracted to variables yet — good first refactor):
  - Background: `#141414`, `#111`, `#0d0d0d`
  - Accent: `#cc2200`, `#8b0000`, `#ff4422`
  - Text: `#e8e0d0`, `#ccc`, `#666`
  - Border: `#2a2a2a`, `#3a3a3a`

---

## Signal / Slot Map

| Signal                       | Emitter          | Connected to                        |
| ---------------------------- | ---------------- | ----------------------------------- |
| `wad_selected(dict)`         | `WadListWidget`  | `MainWindow._on_wad_selected`       |
| `launch_requested(int, str)` | `WadDetailPanel` | `MainWindow._on_launch`             |
| `delete_requested(int)`      | `WadDetailPanel` | `MainWindow._on_delete`             |
| `tags_changed(int, list)`    | `WadDetailPanel` | `MainWindow._on_tags_changed`       |
| `wad_launched(dict)`         | `LastPlayedBar`  | `MainWindow._on_launch_from_recent` |

---

## What's Implemented (PoC)

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
- [x] **Map list display** — `maplist.py` uses `omgifol` to enumerate all map marker lumps (`MAP##` / `E#M#`) from the WAD. If a `MAPINFO`, `ZMAPINFO`, or `UMAPINFO` lump is present, it is parsed to produce `MAP01: Level Name` formatted lines; otherwise plain map names are used. The result is stored as a newline-separated `map_list` TEXT column in the DB. In the detail panel a `MapListWidget` (compact scrollable `QTextEdit`, 180 px wide) appears as a new column between the meta rows and the TITLEPIC, and is hidden automatically when no map data is available. Lazy extraction runs on WAD select for pre-existing library entries (mirrors titlepic pattern).

## Planned / Nice-to-Haves (not yet implemented)

- [x] **Auto-update** — `updater.py` checks `https://api.github.com/repos/exequiel-mleziva/wad-evoker/releases/latest` on boot (2 s delay, background `QThread`). If a newer tag exists, user is prompted to install; download replaces app files in-place and `os.execv` restarts. Settings dialog exposes a **Check for Updates** button with inline status feedback and an **Update Now** button.
- [ ] **Multiple named source port profiles** — e.g. "GZDoom", "DSDA", "Crispy" selectable per-launch or as default
- [ ] **Time played tracking** — store `play_duration_seconds` in `wads` table; hook into process monitoring via `subprocess` + `time`
- [ ] **Screenshot support** — store screenshot paths, display in detail panel
- [ ] **Stats** — similar to DoomLauncher (https://github.com/nstlaurent/DoomLauncher): kills, deaths, secrets per session
- [ ] **IWAD selection** — let user specify the base IWAD (`doom2.wad`, `doom.wad`, etc.) passed via `-iwad`
- [ ] **Extra args per WAD** — store and pass custom launch args (e.g. `-skill 4 -warp 1`)
- [ ] **Edit metadata** — in-app editing of title, author, description fields
- [ ] **Sort / filter** — sort library by title, date added, last played; filter by tag
- [ ] **Packaging** — `pyproject.toml`, `.desktop` file for Linux app launcher integration, optional PyInstaller bundle
- [x] Add maplist display, with support for MAPINFO to get the maps names (if available, if not just display the maps that are modified in the custom wad)

---

## Running

```bash
./run.sh
```

`run.sh` handles full environment setup automatically:

1. Checks for `.venv/bin/activate` — if missing, creates the virtual environment via `python3 -m venv`
2. If venv creation fails (e.g. `ensurepip` not available), detects the Python version and runs `sudo apt-get install -y python3.X-venv` on apt-based systems (Debian/Ubuntu/Kubuntu), then retries
3. On non-apt systems, prints a clear error and exits
4. Activates the venv, upgrades `pip`, installs `requirements.txt`, then launches `main.py`

Must be run from inside the `wad-evoker/` directory so Python resolves the `ui` package correctly.
