import json
import os
import sys
import zipfile
import shutil
import tempfile
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import time

from PyQt6.QtCore import QThread, pyqtSignal

from version import __version__

GITHUB_REPO = "nathan-hyan/wad-evoker"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_LATEST_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"


def _cache_path():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "wad-evoker", "update_check.json")


def _read_cache():
    path = _cache_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_cache(payload):
    path = _cache_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except Exception:
        # Cache failures should never break update checks.
        pass


def _version_tuple(v):
    v = v.lstrip("v")
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def is_running_as_appimage():
    """Return True when the app is executing inside an AppImage."""
    return bool(os.environ.get("APPIMAGE"))


def _latest_release_tag_via_redirect():
    """Resolve the latest release tag without using the GitHub API.

    This hits the public /releases/latest endpoint, which redirects to
    /releases/tag/<tag>. This is significantly less likely to trigger API
    rate limiting than api.github.com.
    """
    req = Request(
        RELEASES_LATEST_URL,
        headers={
            "User-Agent": f"wad-evoker/{__version__}",
        },
    )
    with urlopen(req, timeout=10) as resp:
        final_url = resp.geturl()

    marker = "/releases/tag/"
    idx = final_url.find(marker)
    if idx == -1:
        raise RuntimeError("Could not resolve latest release tag.")
    return final_url[idx + len(marker):]


def _github_api_headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"wad-evoker/{__version__}",
    }
    token = (
        os.environ.get("WAD_EVOKER_GITHUB_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GITHUB_API_TOKEN")
    )
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def check_for_update():
    """Check GitHub for the latest release.

    Returns a dict with update info if a newer version exists, or None if
    already up to date. Raises on network/parse errors.
    """
    # Cooldown cache: prevents hammering endpoints if a user repeatedly clicks.
    cache = _read_cache()
    now = int(time.time())
    cooldown_seconds = 60
    if cache.get("checked_at") and (now - int(cache.get("checked_at", 0)) < cooldown_seconds):
        cached = cache.get("result")
        if cached is None:
            return None
        if isinstance(cached, dict) and cached.get("latest"):
            if _version_tuple(cached.get("latest", "")) > _version_tuple(__version__):
                return cached
            return None

    # Prefer non-API redirect-based check to avoid GitHub API rate limits.
    tag = _latest_release_tag_via_redirect()
    latest_version = tag.lstrip("v")
    html_url = f"https://github.com/{GITHUB_REPO}/releases/tag/{tag}"
    zipball_url = f"https://github.com/{GITHUB_REPO}/archive/refs/tags/{tag}.zip"

    # AppImage updates require a stable binary URL. We only consult the GitHub API
    # to find the AppImage asset when we are actually running as an AppImage.
    appimage_url = ""
    if is_running_as_appimage():
        req = Request(API_URL, headers=_github_api_headers())
        try:
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".AppImage") and "x86_64" in name:
                    appimage_url = asset.get("browser_download_url", "")
                    break
        except HTTPError as e:
            # If the API is rate limited, still allow non-AppImage update flows.
            if e.code == 403:
                raise RuntimeError("GitHub API rate limit exceeded. Try again later or set GITHUB_TOKEN.")
            raise

    if _version_tuple(latest_version) > _version_tuple(__version__):
        result = {
            "current": __version__,
            "latest": latest_version,
            "tag": tag,
            "zipball_url": zipball_url,
            "appimage_url": appimage_url,
            "html_url": html_url,
        }
        _write_cache({"checked_at": now, "result": result})
        return result
    _write_cache({"checked_at": now, "result": None})
    return None


def download_and_apply_appimage_update(appimage_url):
    """Download the new AppImage release and replace the running AppImage in-place."""
    current_appimage = os.environ.get("APPIMAGE")
    if not current_appimage:
        raise RuntimeError("Not running as an AppImage — cannot apply AppImage update.")

    req = Request(appimage_url, headers={"User-Agent": f"wad-evoker/{__version__}"})
    with urlopen(req, timeout=120) as resp:
        new_data = resp.read()

    tmp_path = current_appimage + ".update"
    with open(tmp_path, "wb") as f:
        f.write(new_data)

    os.chmod(tmp_path, 0o755)
    os.replace(tmp_path, current_appimage)


def download_and_apply_update(zipball_url):
    """Download the release zip and overwrite app files in-place."""
    app_dir = os.path.dirname(os.path.abspath(__file__))

    req = Request(zipball_url, headers={"User-Agent": f"wad-evoker/{__version__}"})
    with urlopen(req, timeout=60) as resp:
        zip_data = resp.read()

    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = os.path.join(tmp_dir, "update.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_data)

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmp_dir)

        # GitHub zips contain a single top-level folder like owner-repo-sha/
        extracted = [
            d for d in os.listdir(tmp_dir)
            if os.path.isdir(os.path.join(tmp_dir, d)) and d != "__MACOSX"
        ]
        if not extracted:
            raise RuntimeError("Could not find extracted update folder.")

        src_dir = os.path.join(tmp_dir, extracted[0])

        for item in os.listdir(src_dir):
            src = os.path.join(src_dir, item)
            dst = os.path.join(app_dir, item)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)


def restart_app():
    """Replace the current process with a fresh instance of the app."""
    appimage = os.environ.get("APPIMAGE")
    if appimage and os.path.isfile(appimage):
        os.execv(appimage, [appimage] + sys.argv[1:])
    else:
        os.execv(sys.executable, [sys.executable] + sys.argv)


# ── QThread workers ───────────────────────────────────────────────────────────

class UpdateCheckWorker(QThread):
    update_available = pyqtSignal(str, str, str, str)  # latest_version, zipball_url, html_url, appimage_url
    up_to_date = pyqtSignal(str)                        # current_version
    check_failed = pyqtSignal(str)                      # error message

    def run(self):
        try:
            result = check_for_update()
            if result:
                self.update_available.emit(
                    result["latest"],
                    result["zipball_url"],
                    result["html_url"],
                    result["appimage_url"],
                )
            else:
                self.up_to_date.emit(__version__)
        except Exception as e:
            self.check_failed.emit(str(e))


class UpdateDownloadWorker(QThread):
    finished = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, zipball_url, appimage_url="", parent=None):
        super().__init__(parent)
        self._url = zipball_url
        self._appimage_url = appimage_url

    def run(self):
        try:
            if is_running_as_appimage() and self._appimage_url:
                download_and_apply_appimage_update(self._appimage_url)
            else:
                download_and_apply_update(self._url)
            self.finished.emit()
        except Exception as e:
            self.failed.emit(str(e))
