import json
import os
import sys
import zipfile
import shutil
import tempfile
from urllib.request import urlopen, Request
from urllib.error import URLError

from PyQt6.QtCore import QThread, pyqtSignal

from version import __version__

GITHUB_REPO = "nathan-hyan/wad-evoker"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _version_tuple(v):
    v = v.lstrip("v")
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def is_running_as_appimage():
    """Return True when the app is executing inside an AppImage."""
    return bool(os.environ.get("APPIMAGE"))


def check_for_update():
    """Check GitHub for the latest release.

    Returns a dict with update info if a newer version exists, or None if
    already up to date. Raises on network/parse errors.
    """
    req = Request(
        API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"wad-evoker/{__version__}",
        },
    )
    with urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())

    tag = data.get("tag_name", "")
    latest_version = tag.lstrip("v")
    zipball_url = data.get("zipball_url", "")
    html_url = data.get("html_url", "")

    appimage_url = ""
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if name.endswith(".AppImage") and "x86_64" in name:
            appimage_url = asset.get("browser_download_url", "")
            break

    if _version_tuple(latest_version) > _version_tuple(__version__):
        return {
            "current": __version__,
            "latest": latest_version,
            "tag": tag,
            "zipball_url": zipball_url,
            "appimage_url": appimage_url,
            "html_url": html_url,
        }
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
