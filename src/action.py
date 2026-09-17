from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.cache import Cache
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

    if arg == "cmd:auth":
        # Launch terminal with gh auth status
        subprocess.run(["open", "-a", "Terminal"])
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
