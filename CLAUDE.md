# Wad Evoker — Project Context

A Python + PyQt6 desktop WAD library manager and launcher for classic Doom (1993).
Dark, terminal-aesthetic UI. Linux-native, but cross-platform via PyQt6 (Windows/macOS compatible).

**⚠️ IMPORTANT**: Always update the relevant `docs/` file after completing tasks — document fixes, new features, and architectural changes in the appropriate section.

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
├── wad_importer.py          # File import: .wad, .pk3, .zip extraction + .txt metadata parser + find_deh_files()
├── process_watcher.py       # QThread that monitors a launched subprocess and emits (wad_id, elapsed_seconds) on exit
├── sourceport.py            # Source port config (read/write binary path) + subprocess launch (with -deh support)
├── version.py               # Single source of truth for __version__ (e.g. "1.0.0")
├── updater.py               # Auto-update: GitHub release check, zip download, file replacement, restart
├── requirements.txt         # PyQt6, omgifol, Pillow
├── README.md
├── docs/                    # Extended documentation (see below)
└── ui/
    ├── __init__.py
    ├── main_window.py       # Main window: toolbar, drag-drop, search, splitter layout
    ├── wad_list.py          # Left panel: QListWidget of WADs (with WadItemDelegate for [DEH] badge)
    ├── wad_detail.py        # Right panel: metadata display, tags, launch button, DEH badge row
    ├── wad_edit_dialog.py   # Modal WAD metadata editor + sidecar .txt preview
    ├── last_played.py       # Top "Recent" horizontal card strip
    ├── settings_dialog.py        # Source port binary picker dialog
    ├── update_progress_dialog.py  # Modal progress bar shown during auto-update download/install
    ├── files_launch_dialog.py     # Modal multi-file selection dialog shown before launch
    └── styled_checkbox.py         # Shared StyledCheckBox widget (custom painted, blood-red indicator)
```

---

## Documentation

| File                                           | Contents                                                   |
| ---------------------------------------------- | ---------------------------------------------------------- |
| [`docs/architecture.md`](docs/architecture.md) | Data storage paths, database schema, signal/slot map       |
| [`docs/behaviours.md`](docs/behaviours.md)     | Import, launch, edit, search, tags, source port flows      |
| [`docs/ui.md`](docs/ui.md)                     | Styling tokens, shared UI components (`StyledCheckBox`)    |
| [`docs/roadmap.md`](docs/roadmap.md)           | Implemented features checklist, planned/nice-to-have items |
| [`docs/bugs.md`](docs/bugs.md)                 | Known bugs and fix history with root cause analysis        |

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
