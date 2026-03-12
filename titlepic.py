import os
import hashlib
import zipfile
import tempfile

TITLEPIC_DIR = os.path.expanduser("~/.config/wad-evoker/titlepics")


def ensure_dir():
    os.makedirs(TITLEPIC_DIR, exist_ok=True)


def _cache_path(filepath):
    h = hashlib.md5(filepath.encode()).hexdigest()[:12]
    return os.path.join(TITLEPIC_DIR, f"{h}.png")


def extract_titlepic(filepath):
    """
    Try to extract TITLEPIC from a WAD or PK3 file.
    Returns path to a cached PNG, or None if unavailable.
    Requires: omgifol + Pillow (optional — silently returns None if missing).
    """
    if not filepath or not os.path.isfile(filepath):
        return None

    cache = _cache_path(filepath)
    if os.path.exists(cache):
        return cache

    ensure_dir()
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".wad":
        return _from_wad(filepath, cache)
    elif ext == ".pk3":
        return _from_pk3(filepath, cache)
    return None


# ── WAD ───────────────────────────────────────────────────────────────────────

def _from_wad(wad_path, cache_path):
    try:
        from omg import WAD
    except ImportError:
        return None

    try:
        w = WAD(wad_path)

        if "TITLEPIC" not in w.graphics:
            return None

        img = w.graphics["TITLEPIC"].to_Image("RGBA")
        img.save(cache_path, "PNG")
        return cache_path
    except Exception:
        return None


# ── PK3 (ZIP) ─────────────────────────────────────────────────────────────────

def _from_pk3(pk3_path, cache_path):
    """
    PK3 is a ZIP.  Strategy (in order):
      1. Direct PNG/JPG named TITLEPIC anywhere in the archive (UZDoom-style).
      2. Raw Doom-format graphic lump named TITLEPIC inside the archive.
      3. Any embedded .wad inside the PK3 — recurse into it with omgifol.
    """
    try:
        with zipfile.ZipFile(pk3_path, "r") as z:
            names_lower = {n.lower(): n for n in z.namelist()}

            # ── Strategy 1: direct image file ─────────────────────────────
            for candidate in (
                "graphics/titlepic.png",
                "titlepic.png",
                "graphics/titlepic.jpg",
                "titlepic.jpg",
            ):
                actual = names_lower.get(candidate)
                if actual:
                    result = _save_image_bytes(z.read(actual), cache_path)
                    if result:
                        return result

            # ── Strategy 2: raw Doom graphic lump in archive ───────────────
            for candidate in (
                "graphics/titlepic",
                "titlepic",
            ):
                actual = names_lower.get(candidate)
                if actual:
                    result = _decode_doom_graphic(z.read(actual), cache_path)
                    if result:
                        return result

            # ── Strategy 3: embedded WAD files ────────────────────────────
            wad_entries = [n for n in z.namelist() if n.lower().endswith(".wad")]
            if wad_entries:
                with tempfile.TemporaryDirectory() as tmpdir:
                    for entry in wad_entries:
                        z.extract(entry, tmpdir)
                        embedded = os.path.join(tmpdir, entry)
                        result = _from_wad(embedded, cache_path)
                        if result:
                            return result

    except (zipfile.BadZipFile, OSError):
        pass

    return None


def _save_image_bytes(data, cache_path):
    """Verify bytes are a valid image (via Pillow) and save as PNG."""
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(data))
        img.save(cache_path, "PNG")
        return cache_path
    except Exception:
        return None


def _decode_doom_graphic(data, cache_path):
    """Decode a raw Doom-format graphic lump using omgifol."""
    try:
        from omg.lump import Graphic
        g = Graphic(data)
        img = g.to_Image("RGBA")
        img.save(cache_path, "PNG")
        return cache_path
    except Exception:
        return None
