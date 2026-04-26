import json
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


# ── FULL MAPINFO PARSER ──────────────────────────────────────────────────────

def extract_mapinfo_data(filepath):
    """
    Extract full MAPINFO/ZMAPINFO/UMAPINFO data from a WAD or PK3.
    Returns a dict (ready for JSON serialization) with keys:
      - maps: {MAP_NAME: {title, music, sky, next, secretnext, par, cluster, ...}}
      - episodes: [{start_map, name, pic}]
      - skills: [{name, key, ...}]
      - clusters: {N: {flat, exittext, entertext, ...}}
      - source: "MAPINFO" | "ZMAPINFO" | "UMAPINFO" | None
    Returns None if no MAPINFO lump found.
    """
    if not filepath or not os.path.isfile(filepath):
        return None

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".wad":
        return _full_mapinfo_from_wad(filepath)
    elif ext == ".pk3":
        return _full_mapinfo_from_pk3(filepath)
    return None


def _full_mapinfo_from_wad(wad_path):
    try:
        from omg import WAD
    except ImportError:
        return None

    try:
        w = WAD(wad_path)
        for lump_name in ("ZMAPINFO", "MAPINFO", "UMAPINFO"):
            for group_attr in ("txdefs", "data"):
                try:
                    group = getattr(w, group_attr, None)
                    if group is not None and lump_name in group:
                        raw = group[lump_name].data
                        text = raw.decode("latin-1", errors="replace")
                        is_umapinfo = (lump_name == "UMAPINFO")
                        result = _parse_full_mapinfo(text, umapinfo=is_umapinfo)
                        if result:
                            result["source"] = lump_name
                            return result
                except Exception:
                    pass
    except Exception:
        pass
    return None


def _full_mapinfo_from_pk3(pk3_path):
    try:
        with zipfile.ZipFile(pk3_path, "r") as z:
            names_lower = {n.lower(): n for n in z.namelist()}
            for candidate, is_umapinfo in [
                ("zmapinfo.txt", False), ("zmapinfo", False),
                ("mapinfo.txt", False), ("mapinfo", False),
                ("umapinfo.txt", True), ("umapinfo", True),
            ]:
                actual = names_lower.get(candidate)
                if actual:
                    try:
                        text = z.read(actual).decode("latin-1", errors="replace")
                        result = _parse_full_mapinfo(text, umapinfo=is_umapinfo)
                        if result:
                            src = candidate.replace(".txt", "").upper()
                            result["source"] = src
                            return result
                    except Exception:
                        pass

            # Try embedded WADs
            wad_entries = [n for n in z.namelist() if n.lower().endswith(".wad")]
            if wad_entries:
                with tempfile.TemporaryDirectory() as tmpdir:
                    for entry in wad_entries:
                        z.extract(entry, tmpdir)
                        embedded = os.path.join(tmpdir, entry)
                        result = _full_mapinfo_from_wad(embedded)
                        if result:
                            return result
    except Exception:
        pass
    return None


def _strip_comments(text):
    """Remove C-style // and /* ... */ comments from MAPINFO text."""
    # Block comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # Line comments
    text = re.sub(r'//[^\n]*', '', text)
    return text


def _tokenize_blocks(text):
    """
    Yield (block_type, header_tokens, body_text) tuples from MAPINFO text.
    block_type: 'map', 'episode', 'cluster', 'clusterdef', 'skill',
                'clearepisodes', 'clearskills', 'defaultmap', 'adddefaultmap', 'gameinfo'
    header_tokens: list of tokens on the same line as the block keyword
    body_text: text inside { ... } braces, or '' if no braces
    """
    text = _strip_comments(text)
    # Split into tokens while preserving quoted strings and braces
    i = 0
    length = len(text)
    tokens = []

    while i < length:
        c = text[i]
        if c in ' \t\r':
            i += 1
        elif c == '\n':
            tokens.append('\n')
            i += 1
        elif c == '{':
            tokens.append('{')
            i += 1
        elif c == '}':
            tokens.append('}')
            i += 1
        elif c == '"':
            # Quoted string
            j = i + 1
            while j < length and text[j] != '"':
                if text[j] == '\\' and j + 1 < length:
                    j += 2
                else:
                    j += 1
            tokens.append(text[i:j + 1] if j < length else text[i:])
            i = j + 1
        elif c == '=':
            tokens.append('=')
            i += 1
        elif c == ',':
            tokens.append(',')
            i += 1
        else:
            # Unquoted word
            j = i
            while j < length and text[j] not in ' \t\r\n{}=",' :
                j += 1
            tokens.append(text[i:j])
            i = j

    # Now walk the tokens and identify top-level blocks
    BLOCK_KEYWORDS = {
        'map', 'defaultmap', 'adddefaultmap', 'gameinfo', 'gamedef',
        'episode', 'clearepisodes', 'clearskills',
        'cluster', 'clusterdef', 'skill',
    }

    idx = 0
    total = len(tokens)

    while idx < total:
        # Skip newlines at top level
        if tokens[idx] == '\n':
            idx += 1
            continue

        tok_lower = tokens[idx].lower()
        if tok_lower not in BLOCK_KEYWORDS:
            idx += 1
            continue

        block_type = tok_lower
        idx += 1

        # Collect header tokens (until newline or opening brace)
        header = []
        while idx < total and tokens[idx] not in ('{', '\n'):
            header.append(tokens[idx])
            idx += 1

        # Skip newlines before potential brace
        while idx < total and tokens[idx] == '\n':
            idx += 1

        # Collect body if braced
        body_tokens = []
        if idx < total and tokens[idx] == '{':
            idx += 1
            depth = 1
            while idx < total and depth > 0:
                if tokens[idx] == '{':
                    depth += 1
                elif tokens[idx] == '}':
                    depth -= 1
                    if depth == 0:
                        idx += 1
                        break
                body_tokens.append(tokens[idx])
                idx += 1

        body_text = ' '.join(t for t in body_tokens if t != '\n')
        yield (block_type, header, body_text)


def _unquote(s):
    """Remove surrounding quotes from a string token."""
    if s and len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def _parse_body_props(body_text):
    """Parse 'key = value' pairs from a block body into a dict."""
    props = {}
    # Split on whitespace while respecting quoted strings
    tokens = re.findall(r'"[^"]*"|[^\s,=]+|=|,', body_text)

    i = 0
    total = len(tokens)
    while i < total:
        key = tokens[i]
        if key == '=' or key == ',':
            i += 1
            continue

        # Check for '=' next
        if i + 1 < total and tokens[i + 1] == '=':
            # key = value [, value2, ...]
            i += 2  # skip key and '='
            values = []
            while i < total and tokens[i] != '=' and not (
                i + 1 < total and tokens[i + 1] == '='
                and tokens[i] not in (',', '=')
                and not tokens[i].startswith('"')
            ):
                if tokens[i] == ',':
                    i += 1
                    continue
                values.append(_unquote(tokens[i]))
                i += 1
                # Check if next is a comma (continuation)
                if i < total and tokens[i] == ',':
                    i += 1
                    continue
                break

            key_lower = key.lower()
            if len(values) == 1:
                props[key_lower] = values[0]
            elif len(values) > 1:
                props[key_lower] = values
            else:
                props[key_lower] = True
        else:
            # Bare keyword (flag)
            props[key.lower()] = True
            i += 1

    return props


def _parse_full_mapinfo(text, umapinfo=False):
    """
    Parse full MAPINFO/ZMAPINFO/UMAPINFO text into a structured dict.
    Returns dict with maps, episodes, skills, clusters — or None if nothing found.
    """
    maps = {}
    episodes = []
    skills = []
    clusters = {}
    clear_episodes = False
    clear_skills = False

    for block_type, header, body_text in _tokenize_blocks(text):

        if block_type == 'clearepisodes':
            clear_episodes = True
            episodes = []

        elif block_type == 'clearskills':
            clear_skills = True
            skills = []

        elif block_type == 'map':
            map_name = header[0].upper() if header else None
            if not map_name:
                continue

            map_title = None
            if len(header) >= 2:
                # Skip 'lookup' keyword if present
                title_idx = 1
                if header[1].lower() == 'lookup' and len(header) >= 3:
                    title_idx = 2
                map_title = _unquote(header[title_idx])

            props = _parse_body_props(body_text)
            entry = {}

            if map_title:
                entry["title"] = map_title
            # UMAPINFO uses 'levelname', ZDoom uses title on the header line
            if "levelname" in props:
                entry["title"] = props["levelname"]

            for prop_key, entry_key in [
                ("music", "music"),
                ("sky1", "sky"),
                ("skytexture", "sky"),
                ("next", "next"),
                ("nextsecret", "secretnext"),
                ("secretnext", "secretnext"),
                ("par", "par"),
                ("partime", "par"),
                ("cluster", "cluster"),
                ("levelnum", "levelnum"),
                ("titlepatch", "titlepatch"),
                ("author", "author"),
                ("label", "label"),
            ]:
                if prop_key in props:
                    val = props[prop_key]
                    if entry_key == "par":
                        try:
                            val = int(val)
                        except (ValueError, TypeError):
                            pass
                    if entry_key == "cluster" or entry_key == "levelnum":
                        try:
                            val = int(val)
                        except (ValueError, TypeError):
                            pass
                    entry[entry_key] = val

            # UMAPINFO episode definition inside map block
            if "episode" in props:
                ep_val = props["episode"]
                if isinstance(ep_val, list):
                    ep_entry = {"start_map": map_name}
                    if len(ep_val) >= 1:
                        ep_entry["pic"] = ep_val[0]
                    if len(ep_val) >= 2:
                        ep_entry["name"] = ep_val[1]
                    if len(ep_val) >= 3:
                        ep_entry["key"] = ep_val[2]
                    episodes.append(ep_entry)
                elif isinstance(ep_val, str):
                    episodes.append({"start_map": map_name, "name": ep_val})

            if entry:
                maps[map_name] = entry

        elif block_type == 'episode':
            # ZDoom style: episode MAP01 { name = "..." picname = "..." }
            start_map = header[0].upper() if header else None
            props = _parse_body_props(body_text)
            ep_entry = {}
            if start_map:
                ep_entry["start_map"] = start_map
            if "name" in props:
                ep_entry["name"] = props["name"]
            if "picname" in props:
                ep_entry["pic"] = props["picname"]
            if "key" in props:
                ep_entry["key"] = props["key"]
            # Header may also have the name as second token
            if "name" not in ep_entry and len(header) >= 2:
                ep_entry["name"] = _unquote(header[1])
            if ep_entry:
                episodes.append(ep_entry)

        elif block_type in ('cluster', 'clusterdef'):
            cluster_id = None
            if header:
                try:
                    cluster_id = int(header[0])
                except (ValueError, TypeError):
                    cluster_id = header[0]
            props = _parse_body_props(body_text)
            entry = {}
            for prop_key, entry_key in [
                ("flat", "flat"),
                ("music", "music"),
                ("exittext", "exittext"),
                ("entertext", "entertext"),
                ("exittextislump", "exittextislump"),
                ("entertextislump", "entertextislump"),
            ]:
                if prop_key in props:
                    entry[prop_key] = props[prop_key]
            if cluster_id is not None and entry:
                clusters[str(cluster_id)] = entry

        elif block_type == 'skill':
            skill_name = _unquote(header[0]) if header else None
            props = _parse_body_props(body_text)
            entry = {}
            if skill_name:
                entry["name"] = skill_name
            if "name" in props:
                entry["name"] = props["name"]
            if "key" in props:
                entry["key"] = props["key"]
            if "ammofactor" in props:
                entry["ammofactor"] = props["ammofactor"]
            if "damagefactor" in props:
                entry["damagefactor"] = props["damagefactor"]
            if "spawnfilter" in props:
                entry["spawnfilter"] = props["spawnfilter"]
            if "picname" in props:
                entry["pic"] = props["picname"]
            if entry.get("name"):
                skills.append(entry)

    # Build result
    has_data = maps or episodes or skills or clusters
    if not has_data:
        return None

    result = {
        "maps": maps,
        "episodes": episodes,
        "skills": skills,
        "clusters": clusters,
    }
    if clear_episodes:
        result["clear_episodes"] = True
    if clear_skills:
        result["clear_skills"] = True
    return result


def mapinfo_data_to_json(data):
    """Serialize MAPINFO data dict to JSON string for DB storage."""
    if not data:
        return None
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


def mapinfo_data_from_json(json_str):
    """Deserialize MAPINFO data from JSON string."""
    if not json_str:
        return None
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None
