import configparser
import os
import subprocess

CONFIG_PATH = os.path.expanduser("~/.config/wad-evoker/config.ini")


def _get_config():
    cfg = configparser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        cfg.read(CONFIG_PATH)
    return cfg


def _save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        cfg.write(f)


def get_source_port():
    """Return the configured source port binary path, or empty string."""
    cfg = _get_config()
    return cfg.get("sourceport", "binary", fallback="")


def set_source_port(binary_path):
    cfg = _get_config()
    if "sourceport" not in cfg:
        cfg["sourceport"] = {}
    cfg["sourceport"]["binary"] = binary_path
    _save_config(cfg)


def launch_wad(wad_filepath, extra_args=None):
    """
    Launch a WAD with the configured source port.
    Returns (success: bool, error_message: str)
    """
    binary = get_source_port()
    if not binary:
        return False, "No source port configured. Set one in Settings."
    if not os.path.isfile(binary):
        return False, f"Source port binary not found:\n{binary}"
    if not os.access(binary, os.X_OK):
        return False, f"Source port binary is not executable:\n{binary}"

    cmd = [binary, "-file", wad_filepath]
    if extra_args:
        cmd.extend(extra_args)

    try:
        subprocess.Popen(cmd)
        return True, ""
    except Exception as e:
        return False, str(e)
