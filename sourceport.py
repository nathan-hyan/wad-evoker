import configparser
import os
import subprocess

CONFIG_PATH = os.path.expanduser("~/.config/wad-evoker/config.ini")

_SECTION_PREFIX = "sourceport_"


# ── Config helpers ────────────────────────────────────────────────────────────

def _get_config():
    cfg = configparser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        cfg.read(CONFIG_PATH)
    _migrate_legacy(cfg)
    return cfg


def _save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        cfg.write(f)


def _migrate_legacy(cfg):
    """One-time migration: convert old single [sourceport] binary= to a profile."""
    old_binary = cfg.get("sourceport", "binary", fallback="")
    if not old_binary:
        return
    # Already migrated?
    if int(cfg.get("sourceport", "next_id", fallback="0")) > 0:
        return
    pid = 1
    section = f"{_SECTION_PREFIX}{pid}"
    name = os.path.splitext(os.path.basename(old_binary))[0] or "Default"
    cfg[section] = {"name": name, "binary": old_binary}
    if "sourceport" not in cfg:
        cfg["sourceport"] = {}
    cfg["sourceport"]["active"] = str(pid)
    cfg["sourceport"]["next_id"] = str(pid + 1)
    cfg.remove_option("sourceport", "binary")
    _save_config(cfg)


# ── Profile CRUD ──────────────────────────────────────────────────────────────

def get_profiles():
    """Return list of dicts: [{"id": int, "name": str, "binary": str}, ...]."""
    cfg = _get_config()
    profiles = []
    for section in cfg.sections():
        if section.startswith(_SECTION_PREFIX):
            try:
                pid = int(section[len(_SECTION_PREFIX):])
            except ValueError:
                continue
            profiles.append({
                "id": pid,
                "name": cfg.get(section, "name", fallback=""),
                "binary": cfg.get(section, "binary", fallback=""),
            })
    profiles.sort(key=lambda p: p["id"])
    return profiles


def add_profile(name, binary):
    """Create a new profile. Returns its id."""
    cfg = _get_config()
    if "sourceport" not in cfg:
        cfg["sourceport"] = {}
    next_id = int(cfg.get("sourceport", "next_id", fallback="1"))
    section = f"{_SECTION_PREFIX}{next_id}"
    cfg[section] = {"name": name, "binary": binary}
    cfg["sourceport"]["next_id"] = str(next_id + 1)
    # If this is the first profile, auto-select it
    if not cfg.get("sourceport", "active", fallback=""):
        cfg["sourceport"]["active"] = str(next_id)
    _save_config(cfg)
    return next_id


def update_profile(profile_id, name=None, binary=None):
    """Update an existing profile's name and/or binary."""
    cfg = _get_config()
    section = f"{_SECTION_PREFIX}{profile_id}"
    if not cfg.has_section(section):
        return
    if name is not None:
        cfg.set(section, "name", name)
    if binary is not None:
        cfg.set(section, "binary", binary)
    _save_config(cfg)


def delete_profile(profile_id):
    """Delete a profile. If it was active, select the first remaining or clear."""
    cfg = _get_config()
    section = f"{_SECTION_PREFIX}{profile_id}"
    if cfg.has_section(section):
        cfg.remove_section(section)
    active = int(cfg.get("sourceport", "active", fallback="0"))
    if active == profile_id:
        remaining = get_profiles()
        # Re-read after delete — cfg object still has stale sections removed above
        # but get_profiles() re-reads from disk, so save first
        _save_config(cfg)
        remaining = get_profiles()
        if remaining:
            set_active_profile(remaining[0]["id"])
        else:
            cfg = _get_config()
            cfg["sourceport"]["active"] = ""
            _save_config(cfg)
    else:
        _save_config(cfg)


# ── Active profile ────────────────────────────────────────────────────────────

def get_active_profile_id():
    """Return the active profile id, or 0 if none."""
    cfg = _get_config()
    val = cfg.get("sourceport", "active", fallback="")
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def set_active_profile(profile_id):
    cfg = _get_config()
    if "sourceport" not in cfg:
        cfg["sourceport"] = {}
    cfg["sourceport"]["active"] = str(profile_id)
    _save_config(cfg)


def get_active_binary():
    """Return the binary path of the active profile, or empty string."""
    pid = get_active_profile_id()
    if not pid:
        return ""
    cfg = _get_config()
    section = f"{_SECTION_PREFIX}{pid}"
    return cfg.get(section, "binary", fallback="")


# ── Legacy compatibility shim ─────────────────────────────────────────────────

def get_source_port():
    """Return the active source port binary path, or empty string."""
    return get_active_binary()


def set_source_port(binary_path):
    """Legacy: updates the active profile's binary, or creates one."""
    pid = get_active_profile_id()
    if pid:
        update_profile(pid, binary=binary_path)
    else:
        name = os.path.splitext(os.path.basename(binary_path))[0] or "Default"
        new_id = add_profile(name, binary_path)
        set_active_profile(new_id)


# ── Library settings ──────────────────────────────────────────────────────────

# finished_sort_mode: "separator" | "bottom" | "none"
#   separator = move finished WADs below a "FINISHED" separator (default)
#   bottom    = move finished WADs to end, no separator
#   none      = keep alphabetical order, no reordering

def get_finished_sort_mode():
    cfg = _get_config()
    return cfg.get("library", "finished_sort_mode", fallback="separator")


def set_finished_sort_mode(mode):
    cfg = _get_config()
    if "library" not in cfg:
        cfg["library"] = {}
    cfg["library"]["finished_sort_mode"] = mode
    _save_config(cfg)


def get_hide_finished_from_recent():
    cfg = _get_config()
    return cfg.getboolean("library", "hide_finished_from_recent", fallback=True)


def set_hide_finished_from_recent(value):
    cfg = _get_config()
    if "library" not in cfg:
        cfg["library"] = {}
    cfg["library"]["hide_finished_from_recent"] = str(value).lower()
    _save_config(cfg)


def get_show_finished_badge():
    cfg = _get_config()
    return cfg.getboolean("library", "show_finished_badge", fallback=True)


def set_show_finished_badge(value):
    cfg = _get_config()
    if "library" not in cfg:
        cfg["library"] = {}
    cfg["library"]["show_finished_badge"] = str(value).lower()
    _save_config(cfg)


# ── Launch ────────────────────────────────────────────────────────────────────

def launch_wad(wad_filepath, extra_args=None, deh_files=None, extra_wad_files=None,
               binary_override=None):
    """
    Launch a WAD with the configured source port.
    Returns (success: bool, error_message: str)
    """
    binary = binary_override or get_active_binary()
    if not binary:
        return False, "No source port configured. Add one in Settings → Source Ports."
    if not os.path.isfile(binary):
        return False, f"Source port binary not found:\n{binary}"
    if not os.access(binary, os.X_OK):
        return False, f"Source port binary is not executable:\n{binary}"

    cmd = [binary, "-file", wad_filepath]
    if extra_wad_files:
        cmd.extend(extra_wad_files)
    if deh_files:
        for deh in deh_files:
            cmd.extend(["-deh", deh])
    if extra_args:
        cmd.extend(extra_args)

    try:
        subprocess.Popen(cmd)
        return True, ""
    except Exception as e:
        return False, str(e)
