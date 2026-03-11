# Wad Evoker 💀

A minimal, fast WAD library manager and launcher for classic Doom.

## Features

- Import `.wad`, `.pk3`, and `.zip` files (ZIPs are auto-extracted)
- Drag & drop WADs directly onto the window
- Reads `.txt` sidecar files for title, author, description, year, game, map count
- Tag your WADs (e.g. "Finished", "Favourite", "Co-op")
- "Recent" bar at the top — jump back into a megawad instantly
- Configurable source port binary — works with GZDoom, DSDA-Doom, Crispy Doom, etc.
- Dark, terminal-style UI

## Requirements

- Python 3.10+
- PyQt6

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## First run

1. Click **⚙** (Settings) in the top-right corner
2. Set the path to your source port binary (e.g. `/usr/bin/gzdoom` or `/opt/dsda-doom/dsda-doom`)
3. Click **＋ Add WAD** or drag a `.wad` / `.pk3` / `.zip` onto the window
4. Select a WAD from the library and click **▶ LAUNCH**

## File storage

Imported WADs are copied to `~/.config/wad-evoker/wads/`.  
The library database lives at `~/.config/wad-evoker/library.db`.  
The config (source port path) is at `~/.config/wad-evoker/config.ini`.

## Project structure

```
wad-evoker/
├── main.py              # Entry point
├── db.py                # SQLite library (wads + tags)
├── wad_importer.py      # ZIP extraction, file copy, .txt parsing
├── sourceport.py        # Source port config + subprocess launch
├── requirements.txt
└── ui/
    ├── main_window.py   # Main window, drag-drop, toolbar
    ├── wad_list.py      # Left panel: WAD list
    ├── wad_detail.py    # Right panel: metadata, tags, launch
    ├── last_played.py   # Top "Recent" bar
    └── settings_dialog.py  # Source port picker
```

## Switching source ports

Open **⚙ Settings** and point the binary at any compatible executable.  
No restart needed — the change applies to the next launch.

---

_Nice-to-haves for future iterations: TITLEPIC display, time played tracking, screenshots, multiple named source port profiles._