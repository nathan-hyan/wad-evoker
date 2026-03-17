import os
import re
import shutil
import zipfile
import titlepic
import maplist

WAD_DIR = os.path.expanduser("~/.config/wad-evoker/wads")

SIDECAR_EXTENSIONS = (".txt", ".deh")


def ensure_wad_dir():
    os.makedirs(WAD_DIR, exist_ok=True)


# ── FILE IMPORT ───────────────────────────────────────────────────────────────

def import_file(source_path):
    """
    Accept a .wad, .pk3 or .zip path.
    Returns a list of dicts with keys: filepath, filename, metadata
    (a ZIP may contain multiple WADs).
    Each import creates a named subfolder under WAD_DIR so sidecar files
    (.txt, .deh) live alongside the WAD for future use.
    """
    ensure_wad_dir()
    ext = os.path.splitext(source_path)[1].lower()

    if ext == ".zip":
        return _import_zip(source_path)
    elif ext in (".wad", ".pk3"):
        return [_import_single(source_path)]
    else:
        return []


def _import_single(source_path):
    filename = os.path.basename(source_path)
    base_name = os.path.splitext(filename)[0]
    entry_dir = _make_entry_subdir(base_name)
    dest = os.path.join(entry_dir, filename)
    shutil.copy2(source_path, dest)
    _copy_matching_sidecars(os.path.dirname(source_path), filename, entry_dir)
    txt_meta = _find_and_parse_txt(entry_dir, filename)
    maps = maplist.extract_maps(dest)
    return {
        "filepath": dest,
        "filename": filename,
        "metadata": txt_meta,
        "titlepic_path": titlepic.extract_titlepic(dest),
        "map_list": maplist.format_map_list(maps),
    }


def _import_zip(zip_path):
    results = []
    zip_base = os.path.splitext(os.path.basename(zip_path))[0]
    extract_dir = os.path.join(WAD_DIR, "_extract_tmp")
    os.makedirs(extract_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    # Collect WAD/PK3 files from the extraction
    wad_files = []
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if os.path.splitext(f)[1].lower() in (".wad", ".pk3"):
                wad_files.append((root, f))

    if not wad_files:
        shutil.rmtree(extract_dir, ignore_errors=True)
        return results

    # One subfolder for all WADs from this zip (they belong to the same release)
    entry_dir = _make_entry_subdir(zip_base)

    # Copy every sidecar file (.txt, .deh) from the entire extracted tree
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if os.path.splitext(f)[1].lower() in SIDECAR_EXTENSIONS:
                src = os.path.join(root, f)
                dst = os.path.join(entry_dir, f)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)

    # Copy each WAD into the entry subfolder and build results
    for root, f in wad_files:
        src = os.path.join(root, f)
        dest = _unique_dest_in_dir(f, entry_dir)
        shutil.copy2(src, dest)
        txt_meta = _find_and_parse_txt(entry_dir, os.path.basename(dest))
        maps = maplist.extract_maps(dest)
        results.append({
            "filepath": dest,
            "filename": os.path.basename(dest),
            "metadata": txt_meta,
            "titlepic_path": titlepic.extract_titlepic(dest),
            "map_list": maplist.format_map_list(maps),
        })

    shutil.rmtree(extract_dir, ignore_errors=True)
    return results


def _make_entry_subdir(name):
    """Create a unique subfolder under WAD_DIR for an entry and return its path."""
    candidate = os.path.join(WAD_DIR, name)
    if not os.path.exists(candidate):
        os.makedirs(candidate, exist_ok=True)
        return candidate
    i = 1
    while True:
        candidate = os.path.join(WAD_DIR, f"{name}_{i}")
        if not os.path.exists(candidate):
            os.makedirs(candidate, exist_ok=True)
            return candidate
        i += 1


def _unique_dest_in_dir(filename, dest_dir):
    """Return a unique destination path for filename inside dest_dir."""
    dest = os.path.join(dest_dir, filename)
    if not os.path.exists(dest):
        return dest
    base, ext = os.path.splitext(filename)
    i = 1
    while True:
        candidate = os.path.join(dest_dir, f"{base}_{i}{ext}")
        if not os.path.exists(candidate):
            return candidate
        i += 1


def _copy_matching_sidecars(source_dir, wad_filename, dest_dir):
    """Copy .txt and .deh files whose name matches the WAD basename from source_dir to dest_dir."""
    base = os.path.splitext(wad_filename)[0]
    try:
        for fname in os.listdir(source_dir):
            ext = os.path.splitext(fname)[1].lower()
            if ext in SIDECAR_EXTENSIONS and fname.lower().startswith(base.lower()):
                src = os.path.join(source_dir, fname)
                dst = os.path.join(dest_dir, fname)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
    except OSError:
        pass


def _find_and_parse_txt(directory, wad_filename):
    """Look for a .txt file in the same dir as the wad."""
    base = os.path.splitext(wad_filename)[0]
    for fname in os.listdir(directory):
        if fname.lower().endswith(".txt") and fname.lower().startswith(base.lower()):
            return parse_txt(os.path.join(directory, fname))
    return {}


# ── TXT METADATA PARSER ───────────────────────────────────────────────────────

# Canonical idgames-style field names → our db fields
_FIELD_MAP = {
    "title":            "title",
    "author":           "author",
    "description":      "description",
    "year":             "year",
    "game":             "game",
    "levels released":  "map_count",
    "map count":        "map_count",
    "number of levels": "map_count",
    "number of maps":   "map_count",
}


def parse_txt(txt_path):
    """
    Parse an idgames-format .txt sidecar file.
    Returns a dict with keys matching our db columns.
    """
    meta = {}
    try:
        with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return meta

    current_key = None
    current_val_lines = []

    def flush():
        if current_key and current_val_lines:
            val = " ".join(" ".join(l.split()) for l in current_val_lines).strip()
            if val and current_key not in meta:
                meta[current_key] = val

    for line in lines:
        # Match   Key   :   Value
        m = re.match(r"^([^:]{1,40}?)\s*:\s*(.*)", line)
        if m:
            flush()
            raw_key = m.group(1).strip().lower()
            val = m.group(2).strip()
            current_key = _FIELD_MAP.get(raw_key)
            current_val_lines = [val] if val else []
        elif current_key and line.strip():
            # continuation line
            current_val_lines.append(line.strip())
        else:
            if current_key:
                flush()
            current_key = None
            current_val_lines = []

    flush()
    return meta


def title_from_filename(filename):
    base = os.path.splitext(filename)[0]
    # turn underscores/dashes into spaces, title-case
    return re.sub(r"[_\-]+", " ", base).title()
