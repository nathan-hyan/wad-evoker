import os
import re
import zipfile
import tempfile


def extract_maps(filepath):
    """
    Extract map list from a WAD or PK3 file using omgifol.
    Returns a list of strings:
      - With MAPINFO: ["MAP01: Name", "MAP02: Name", ...]
      - Without:      ["MAP01", "MAP02", ...]
    Returns empty list if not readable or no maps found.
    """
    if not filepath or not os.path.isfile(filepath):
        return []

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".wad":
        return _maps_from_wad(filepath)
    elif ext == ".pk3":
        return _maps_from_pk3(filepath)
    return []


def format_map_list(maps):
    """Convert list of map strings to a newline-separated string for DB storage."""
    return "\n".join(maps) if maps else ""


def get_warp_info(filepath):
    """
    Analyse a WAD/PK3 to decide whether auto-warp is needed.
    Returns (needs_warp: bool, first_map: str or None, has_mapinfo: bool).

    needs_warp is True when:
      - No MAPINFO/ZMAPINFO/UMAPINFO is present, AND
      - The first map lump is not MAP01 or E1M1
    """
    if not filepath or not os.path.isfile(filepath):
        return False, None, False

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".wad":
        return _warp_info_from_wad(filepath)
    elif ext == ".pk3":
        return _warp_info_from_pk3(filepath)
    return False, None, False


def map_to_warp_args(map_name):
    """
    Convert a map lump name to a list of -warp arguments.
    Returns a list like ["-warp", "7"] or ["-warp", "2", "1"], or [] if
    the map name doesn't match a known pattern.
    """
    if not map_name:
        return []
    upper = map_name.upper()

    # MAPxx format
    m = re.match(r'^MAP(\d+)$', upper)
    if m:
        return ["-warp", str(int(m.group(1)))]

    # ExMy format
    m = re.match(r'^E(\d+)M(\d+)$', upper)
    if m:
        return ["-warp", m.group(1), m.group(2)]

    return []


# ── WAD ───────────────────────────────────────────────────────────────────────

def _maps_from_wad(wad_path):
    try:
        from omg import WAD
    except ImportError:
        return []

    try:
        w = WAD(wad_path)
        map_names = sorted(w.maps.keys())
        if not map_names:
            return []

        mapinfo = _parse_mapinfo_from_wad(w)
        return _format_maps(map_names, mapinfo)
    except Exception:
        return []


def _parse_mapinfo_from_wad(w):
    """Try to find and parse MAPINFO/ZMAPINFO/UMAPINFO from a loaded omgifol WAD."""
    for lump_name in ("MAPINFO", "ZMAPINFO", "UMAPINFO"):
        for group_attr in ("txdefs", "data"):
            try:
                group = getattr(w, group_attr, None)
                if group is not None and lump_name in group:
                    raw = group[lump_name].data
                    text = raw.decode("latin-1", errors="replace")
                    result = _parse_mapinfo_text(text)
                    if result:
                        return result
            except Exception:
                pass
    return None


_DEFAULT_FIRST_MAPS = frozenset({"MAP01", "E1M1"})


def _has_mapinfo_lump(w):
    """Return True if the loaded omgifol WAD contains any MAPINFO/ZMAPINFO/UMAPINFO lump."""
    for lump_name in ("MAPINFO", "ZMAPINFO", "UMAPINFO"):
        for group_attr in ("txdefs", "data"):
            try:
                group = getattr(w, group_attr, None)
                if group is not None and lump_name in group:
                    return True
            except Exception:
                pass
    return False


def _warp_info_from_wad(wad_path):
    """Return (needs_warp, first_map, has_mapinfo) for a WAD file."""
    try:
        from omg import WAD
    except ImportError:
        return False, None, False

    try:
        w = WAD(wad_path)
        map_names = sorted(w.maps.keys())
        has_mi = _has_mapinfo_lump(w)
        if not map_names:
            return False, None, has_mi
        first = map_names[0]
        needs = (not has_mi) and (first.upper() not in _DEFAULT_FIRST_MAPS)
        return needs, first, has_mi
    except Exception:
        return False, None, False


def _warp_info_from_pk3(pk3_path):
    """Return (needs_warp, first_map, has_mapinfo) for a PK3 file."""
    try:
        with zipfile.ZipFile(pk3_path, "r") as z:
            names_lower = {n.lower(): n for n in z.namelist()}

            has_mi = any(
                names_lower.get(c) is not None
                for c in ("mapinfo.txt", "zmapinfo.txt", "umapinfo.txt",
                           "mapinfo", "zmapinfo", "umapinfo")
            )

            # Try embedded WAD files for map detection
            wad_entries = [n for n in z.namelist() if n.lower().endswith(".wad")]
            if wad_entries:
                with tempfile.TemporaryDirectory() as tmpdir:
                    for entry in wad_entries:
                        z.extract(entry, tmpdir)
                        embedded = os.path.join(tmpdir, entry)
                        try:
                            from omg import WAD as _WAD
                            w = _WAD(embedded)
                            map_names = sorted(w.maps.keys())
                            if map_names:
                                first = map_names[0]
                                needs = (not has_mi) and (first.upper() not in _DEFAULT_FIRST_MAPS)
                                return needs, first, has_mi
                        except Exception:
                            continue
    except Exception:
        pass
    return False, None, False


# ── PK3 (ZIP) ─────────────────────────────────────────────────────────────────

def _maps_from_pk3(pk3_path):
    """For PK3: check MAPINFO text files and recurse into embedded WADs."""
    try:
        with zipfile.ZipFile(pk3_path, "r") as z:
            names_lower = {n.lower(): n for n in z.namelist()}

            # Try MAPINFO text file directly inside the PK3
            for candidate in ("mapinfo.txt", "zmapinfo.txt", "umapinfo.txt", "mapinfo"):
                actual = names_lower.get(candidate)
                if actual:
                    try:
                        text = z.read(actual).decode("latin-1", errors="replace")
                        mapinfo = _parse_mapinfo_text(text)
                    except Exception:
                        mapinfo = None
                    break
            else:
                mapinfo = None

            # Try embedded WAD files
            wad_entries = [n for n in z.namelist() if n.lower().endswith(".wad")]
            if wad_entries:
                with tempfile.TemporaryDirectory() as tmpdir:
                    for entry in wad_entries:
                        z.extract(entry, tmpdir)
                        embedded = os.path.join(tmpdir, entry)
                        result = _maps_from_wad(embedded)
                        if result:
                            return result
    except Exception:
        pass
    return []


# ── MAPINFO PARSER ────────────────────────────────────────────────────────────

def _parse_mapinfo_text(text):
    """
    Parse MAPINFO / ZMAPINFO / UMAPINFO text.
    Handles both ZDoom block-style and classic single-line formats.
    Returns dict {MAP_NAME_UPPER: display_name} or None if nothing found.
    """
    result = {}

    # ZDoom / UZDoom style: map MAP01 "Level Name" { ... }
    # Also covers: map MAP01 lookup "LANGUAGE_KEY" (ZDoom lookup syntax)
    for m in re.finditer(
        r'^\s*map\s+(\w+)\s+(?:lookup\s+)?"([^"]+)"',
        text, re.IGNORECASE | re.MULTILINE
    ):
        result[m.group(1).upper()] = m.group(2)

    # Classic / unquoted: map MAP01 Level Name  (no braces, no quotes)
    if not result:
        for m in re.finditer(
            r'^\s*map\s+(\w+)\s+([^"\n{]+)',
            text, re.IGNORECASE | re.MULTILINE
        ):
            name = m.group(2).strip()
            if name and name.lower() != "lookup":
                result[m.group(1).upper()] = name

    return result if result else None


# ── FORMAT ────────────────────────────────────────────────────────────────────

def _format_maps(map_names, mapinfo):
    """Build the final list of display strings."""
    if mapinfo:
        out = []
        for name in map_names:
            display = mapinfo.get(name.upper())
            if display:
                out.append(f"{name}: {display}")
            else:
                out.append(name)
        return out
    return list(map_names)
