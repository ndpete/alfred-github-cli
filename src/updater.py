from __future__ import annotations

import json
import plistlib
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

from src.cache import Cache, get_data_dir
from src.gh import GhCli

REPO_NAME = "ndpete/alfred-github-cli"


def get_current_version() -> str:
    """Read the workflow version from info.plist."""
    plist_path = Path(__file__).resolve().parent.parent / "info.plist"
    if plist_path.exists():
        try:
            with plist_path.open("rb") as f:
                data = plistlib.load(f)
                return str(data.get("version", "0.0.0"))
        except Exception:
            pass
    return "0.0.0"


def parse_version(v: str) -> tuple[int, ...]:
    """Parse a semantic version string like '0.2.0', 'v1.5.12', or 'v0.3.0-rc1'."""
    v = v.split("-")[0].split("+")[0].lstrip("v").strip()
    parts = []
    for part in v.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def is_newer_version(latest: str, current: str) -> bool:
    """Return True if latest version is strictly newer than current."""
    return parse_version(latest) > parse_version(current)


def notify(message: str, title: str = "GitHub CLI") -> None:
    """Display a native desktop notification using Alfred's workflow notification (with GitHub icon)."""
    escaped = message.replace('"', '\\"')
    script = (
        f'tell application id "com.runningwithcrayons.Alfred" to '
        f'run trigger "notify" in workflow "com.github.ndpete.alfred-github-cli" '
        f'with argument "{escaped}"'
    )
    try:
        res = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return
    except OSError:
        pass

    fallback = (
        f'tell application id "com.runningwithcrayons.Alfred" to '
        f'display notification "{escaped}" with title "{title}"'
    )
    try:
        subprocess.run(["osascript", "-e", fallback], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def fetch_latest_release(repo: str = REPO_NAME) -> dict[str, Any] | None:
    """Fetch the latest release object from GitHub using gh CLI or urllib fallback."""
    # Attempt 1: via gh CLI
    if GhCli.is_installed() and GhCli.check_auth():
        data = GhCli.run_json(["api", f"repos/{repo}/releases/latest"])
        if data and isinstance(data, dict) and "tag_name" in data:
            return data

    # Attempt 2: via urllib public API
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "alfred-github-cli",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def check_for_updates(cache: Cache, force: bool = False) -> dict[str, Any] | None:
    """Check GitHub for newer releases. Returns release info if an update is available."""
    last_check_str = cache.get_meta("last_update_check")
    last_check = float(last_check_str) if last_check_str else 0.0

    # Only check once every 24 hours unless forced
    if not force and (time.time() - last_check) < 86400:
        latest_ver = cache.get_meta("latest_version")
        if latest_ver and is_newer_version(latest_ver, get_current_version()):
            return {
                "version": latest_ver,
                "download_url": cache.get_meta("latest_download_url"),
                "release_url": cache.get_meta("latest_release_url"),
            }
        return None

    cache.set_meta("last_update_check", str(time.time()))

    release = fetch_latest_release()
    if not release:
        return None

    tag_name = release.get("tag_name", "").lstrip("v")
    current_ver = get_current_version()

    # Find .alfredworkflow asset
    download_url = None
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if name.endswith(".alfredworkflow"):
            download_url = asset.get("browser_download_url")
            break

    if is_newer_version(tag_name, current_ver) and download_url:
        cache.set_meta("latest_version", tag_name)
        cache.set_meta("latest_download_url", download_url)
        cache.set_meta("latest_release_url", release.get("html_url", ""))
        return {
            "version": tag_name,
            "download_url": download_url,
            "release_url": release.get("html_url", ""),
        }
    else:
        # Clear stale update meta if currently on latest
        cache.set_meta("latest_version", "")
        cache.set_meta("latest_download_url", "")
        cache.set_meta("latest_release_url", "")
        return None


def download_and_install_update(cache: Cache) -> tuple[bool, str]:
    """Download the latest .alfredworkflow asset and prompt Alfred to install it."""
    download_url = cache.get_meta("latest_download_url")
    latest_ver = cache.get_meta("latest_version")

    if not download_url or not latest_ver:
        update_info = check_for_updates(cache, force=True)
        if not update_info:
            return False, "No update available."
        download_url = update_info["download_url"]
        latest_ver = update_info["version"]

    notify(f"Downloading update v{latest_ver}...", "GitHub CLI Workflow")

    dest_dir = get_data_dir()
    dest_file = dest_dir / "alfred-github-cli.alfredworkflow"

    req = urllib.request.Request(
        download_url,
        headers={"User-Agent": "alfred-github-cli"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30.0) as resp, open(dest_file, "wb") as f:
            f.write(resp.read())
    except Exception as e:
        msg = f"Failed to download update: {e}"
        notify(msg, "GitHub CLI Workflow")
        return False, msg

    # Clear update flags from cache
    cache.set_meta("latest_version", "")
    cache.set_meta("latest_download_url", "")

    notify(f"Update v{latest_ver} ready. Opening Alfred to install...", "GitHub CLI Workflow")

    # Launch native Alfred workflow updater dialog
    subprocess.run(["open", str(dest_file)], check=False)
    return True, f"Opened installer for v{latest_ver}"
