from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.cache import Cache
from src.gh import GhCli
from src.worker import sync_github_data


def run_action(arg: str) -> None:
    arg = arg.strip()
    if not arg:
        return

    if arg == "cmd:refresh":
        cache = Cache()
        success = sync_github_data(cache)
        if success:
            sys.stdout.write("GitHub repositories refreshed successfully!\n")
        else:
            sys.stderr.write("Failed to refresh GitHub repositories. Check gh auth status.\n")
            sys.exit(1)
        return

    if arg == "cmd:clear-cache":
        cache = Cache()
        db_file = cache.db_path
        if db_file.exists():
            db_file.unlink(missing_ok=True)
            for suffix in ["-wal", "-shm"]:
                p = Path(f"{db_file}{suffix}")
                if p.exists():
                    p.unlink(missing_ok=True)
        sys.stdout.write("Cache cleared successfully!\n")
        return

    if arg == "cmd:update":
        cache = Cache()
        from src.updater import download_and_install_update
        success, msg = download_and_install_update(cache)
        if success:
            sys.stdout.write(f"{msg}\n")
        else:
            sys.stderr.write(f"{msg}\n")
            sys.exit(1)
        return

    if arg == "cmd:check-update":
        cache = Cache()
        from src.updater import check_for_updates, get_current_version
        update_info = check_for_updates(cache, force=True)
        current_ver = get_current_version()
        if update_info:
            sys.stdout.write(f"Update available: v{update_info['version']}! Run '> update' to install.\n")
        else:
            sys.stdout.write(f"Workflow is up to date (v{current_ver}).\n")
        return

    if arg == "cmd:auth":
        cache = Cache()
        if not GhCli.is_installed():
            sys.stdout.write("GitHub CLI ('gh') is not installed. Install via 'brew install gh'.\n")
            return

        if GhCli.check_auth():
            user = cache.get_meta("viewer_login") or GhCli.get_viewer_login() or "authenticated user"
            sys.stdout.write(f"✓ Authenticated as @{user} on GitHub.com\n")
        else:
            script = 'tell application "Terminal" to do script "gh auth login"'
            subprocess.run(["osascript", "-e", script], check=False)
            sys.stdout.write("Not authenticated. Opening Terminal to log in...\n")
        return

    if arg == "cmd:login":
        script = 'tell application "Terminal" to do script "gh auth login"'
        subprocess.run(["osascript", "-e", script], check=False)
        sys.stdout.write("Opening Terminal to log in to GitHub CLI...\n")
        return

    if arg == "cmd:version":
        cache = Cache()
        from src.updater import get_current_version
        current_ver = get_current_version()
        gh_ver = (cache.get_meta("gh_version") if cache else None) or GhCli.get_version()
        gh_desc = f"v{gh_ver}" if gh_ver else "not installed"
        sys.stdout.write(f"Workflow v{current_ver} • gh CLI {gh_desc}\n")
        return

    # Standard URL handling
    if arg.startswith("http://") or arg.startswith("https://"):
        subprocess.run(["open", arg], check=False)
        return

    # Fallback open
    subprocess.run(["open", arg], check=False)


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    run_action(arg)


if __name__ == "__main__":
    main()
