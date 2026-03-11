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

    if _version_tuple(latest_version) > _version_tuple(__version__):
        return {
            "current": __version__,
            "latest": latest_version,
            "tag": tag,
            "zipball_url": zipball_url,
            "html_url": html_url,
        }
    return None


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
    os.execv(sys.executable, [sys.executable] + sys.argv)


# ── QThread workers ───────────────────────────────────────────────────────────

class UpdateCheckWorker(QThread):
    update_available = pyqtSignal(str, str, str)  # latest_version, zipball_url, html_url
    up_to_date = pyqtSignal(str)                   # current_version
    check_failed = pyqtSignal(str)                 # error message

    def run(self):
        try:
            result = check_for_update()
            if result:
                self.update_available.emit(
                    result["latest"],
                    result["zipball_url"],
                    result["html_url"],
                )
            else:
                self.up_to_date.emit(__version__)
        except Exception as e:
            self.check_failed.emit(str(e))


class UpdateDownloadWorker(QThread):
    finished = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, zipball_url, parent=None):
        super().__init__(parent)
        self._url = zipball_url

    def run(self):
        try:
            download_and_apply_update(self._url)
            self.finished.emit()
        except Exception as e:
            self.failed.emit(str(e))
