# Architecture

## Data Storage

All user data lives under `~/.config/wad-evoker/`:

| Path         | Purpose                                                               |
| ------------ | --------------------------------------------------------------------- |
| `library.db` | SQLite database                                                       |
| `wads/`      | Imported WAD/PK3 files — each entry in its own named subfolder        |
| `titlepics/` | Cached TITLEPIC PNGs (md5-named, extracted on import or first select) |
| `config.ini` | Source port binary path                                               |

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
    skip_files_prompt INTEGER DEFAULT 0  -- skip FilesLaunchDialog on next launch
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
