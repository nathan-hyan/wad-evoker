# Architecture

## Data Storage

All user data lives under `~/.config/wad-evoker/`:

| Path         | Purpose                                                               |
| ------------ | --------------------------------------------------------------------- |
| `library.db` | SQLite database                                                       |
| `wads/`      | Imported WAD/PK3 files — each entry in its own named subfolder        |
| `titlepics/` | Cached TITLEPIC PNGs (md5-named, extracted on import or first select) |
| `config.ini` | Source port profiles + library settings                                |

---

## Database Schema

```sql
CREATE TABLE wads (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    title             TEXT NOT NULL,
    filename          TEXT NOT NULL,
    filepath          TEXT NOT NULL UNIQUE,
    author            TEXT,
    description       TEXT,
    year              TEXT,
    game              TEXT,
    map_count         TEXT,
    map_list          TEXT,
    titlepic_path     TEXT,
    added_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_played       TIMESTAMP,
    skip_files_prompt INTEGER DEFAULT 0, -- skip FilesLaunchDialog on next launch
    extra_wads        TEXT,               -- newline-separated extra WAD/PK3 paths
    finished          INTEGER DEFAULT 0,  -- 1 = user marked WAD as finished
    play_duration_seconds INTEGER DEFAULT 0, -- cumulative play time in seconds
    extra_args        TEXT,               -- user-defined extra launch args string
    sourceport_profile_id INTEGER,         -- per-WAD source port profile override (NULL = use active)
    auto_warp         INTEGER DEFAULT 0,  -- 1 = auto-inject -warp on launch
    warp_target       TEXT,               -- override map name for -warp (NULL = auto-detect from first map)
    mapinfo_data      TEXT,               -- JSON blob: full parsed MAPINFO/ZMAPINFO/UMAPINFO data (episodes, skills, per-map props, clusters)
    is_gameplay_mod   INTEGER DEFAULT 0    -- 1 = WAD is a gameplay mod (no maps, loaded alongside other WADs)
);

CREATE TABLE tags (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    wad_id  INTEGER NOT NULL REFERENCES wads(id) ON DELETE CASCADE,
    tag     TEXT NOT NULL,
    UNIQUE(wad_id, tag)
);
```

---

## Signal / Slot Map

| Signal                       | Emitter          | Connected to                        |
| ---------------------------- | ---------------- | ----------------------------------- |
| `wad_selected(dict)`         | `WadListWidget`  | `MainWindow._on_wad_selected`       |
| `launch_requested(int, str)` | `WadDetailPanel` | `MainWindow._on_launch`             |
| `edit_requested(int)`        | `WadDetailPanel` | `MainWindow._on_edit`               |
| `delete_requested(int)`      | `WadDetailPanel` | `MainWindow._on_delete`             |
| `tags_changed(int, list)`    | `WadDetailPanel` | `MainWindow._on_tags_changed`       |
| `wad_launched(dict)`         | `LastPlayedBar`  | `MainWindow._on_launch_from_recent` |
| `play_requested(dict)`       | `WadListWidget`  | `MainWindow._on_launch` (via lambda)|
| `edit_requested(dict)`       | `WadListWidget`  | `MainWindow._on_edit` (via lambda)  |
| `delete_requested(dict)`     | `WadListWidget`  | `MainWindow._on_delete` (via lambda)|
| `finish_toggled(dict)`       | `WadListWidget`  | `MainWindow._on_finish_toggled`     |
| `ProcessWatcher.finished(int, int)` | `ProcessWatcher` | `MainWindow._on_process_finished` |
