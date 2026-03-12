import os
import re
import shutil
import zipfile
import titlepic
import maplist

WAD_DIR = os.path.expanduser("~/.config/wad-evoker/wads")


def ensure_wad_dir():
    os.makedirs(WAD_DIR, exist_ok=True)


# ── FILE IMPORT ───────────────────────────────────────────────────────────────

def import_file(source_path):
    """
    Accept a .wad, .pk3 or .zip path.
    Returns a list of dicts with keys: filepath, filename, metadata
    (a ZIP may contain multiple WADs).
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
    dest = _unique_dest(filename)
    shutil.copy2(source_path, dest)
    txt_meta = _find_and_parse_txt(os.path.dirname(source_path), filename)
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
    extract_dir = os.path.join(WAD_DIR, "_extract_tmp")
    os.makedirs(extract_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    # Walk extracted contents
    for root, _, files in os.walk(extract_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in (".wad", ".pk3"):
                src = os.path.join(root, f)
                dest = _unique_dest(f)
                shutil.copy2(src, dest)
                txt_meta = _find_and_parse_txt(root, f)
                maps = maplist.extract_maps(dest)
                results.append({
                    "filepath": dest,
                    "filename": f,
                    "metadata": txt_meta,
                    "titlepic_path": titlepic.extract_titlepic(dest),
                    "map_list": maplist.format_map_list(maps),
                })

    shutil.rmtree(extract_dir, ignore_errors=True)
    return results


def _unique_dest(filename):
    dest = os.path.join(WAD_DIR, filename)
    if not os.path.exists(dest):
        return dest
    base, ext = os.path.splitext(filename)
    i = 1
    while True:
        candidate = os.path.join(WAD_DIR, f"{base}_{i}{ext}")
        if not os.path.exists(candidate):
            return candidate
        i += 1


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
