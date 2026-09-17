from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any

logger = logging.getLogger("gh")


class GhCli:
    """Wrapper around GitHub CLI (`gh`)."""

    @staticmethod
    def is_installed() -> bool:
        """Check if `gh` executable is found in PATH."""
        return shutil.which("gh") is not None

    @staticmethod
    def check_auth(timeout: float = 3.0) -> bool:
        """Check if `gh` is authenticated."""
        if not GhCli.is_installed():
            return False
        try:
            res = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            # returncode 0 means authenticated
            return res.returncode == 0
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.warning(f"Failed to check gh auth status: {e}")
            return False

    @staticmethod
    def run(args: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
        """Execute a `gh` command safely."""
        cmd = ["gh", *args]
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    @staticmethod
    def run_json(args: list[str], timeout: float = 10.0) -> Any | None:
        """Execute a `gh` command and parse its JSON stdout."""
        try:
            res = GhCli.run(args, timeout=timeout)
            if res.returncode != 0:
                logger.warning(f"gh command failed: {' '.join(args)}: {res.stderr}")
                return None
            return json.loads(res.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
            logger.warning(f"gh JSON execution error: {e}")
            return None

    @staticmethod
    def run_graphql(query: str, variables: dict[str, Any] | None = None, timeout: float = 15.0) -> dict[str, Any] | None:
        """Run a GraphQL query via `gh api graphql`."""
        args = ["api", "graphql", "-f", f"query={query}"]
        if variables:
            for k, v in variables.items():
                args.extend(["-F", f"{k}={v}"])
        res = GhCli.run_json(args, timeout=timeout)
        if isinstance(res, dict) and "data" in res:
            return res["data"]
        return None

    @staticmethod
    def search_repos(query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search repositories globally via `gh search repos`."""
        fields = "fullName,name,description,url,isPrivate,isFork,stargazerCount,updatedAt"
        res = GhCli.run_json([
            "search", "repos", query,
            "--limit", str(limit),
            "--json", fields,
        ])
        return res if isinstance(res, list) else []

    @staticmethod
    def search_prs(query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search PRs globally or filtered by author/assignee."""
        fields = "number,title,url,state,repository,updatedAt"
        res = GhCli.run_json([
            "search", "prs", query,
            "--limit", str(limit),
            "--json", fields,
        ])
        return res if isinstance(res, list) else []

    @staticmethod
    def list_repo_prs(repo: str, limit: int = 25) -> list[dict[str, Any]]:
        """List open pull requests for a specific repository."""
        fields = "number,title,url,state,author,updatedAt"
        res = GhCli.run_json([
            "pr", "list",
            "--repo", repo,
            "--limit", str(limit),
            "--json", fields,
        ])
        return res if isinstance(res, list) else []

    @staticmethod
    def list_repo_issues(repo: str, limit: int = 25) -> list[dict[str, Any]]:
        """List open issues for a specific repository."""
        fields = "number,title,url,state,author,updatedAt"
        res = GhCli.run_json([
            "issue", "list",
            "--repo", repo,
            "--limit", str(limit),
            "--json", fields,
        ])
        return res if isinstance(res, list) else []

    @staticmethod
    def get_viewer_login(timeout: float = 3.0) -> str | None:
        """Get authenticated GitHub username."""
        try:
            res = GhCli.run(["api", "user", "-q", ".login"], timeout=timeout)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return None

    @staticmethod
    def get_version(timeout: float = 3.0) -> str | None:
        """Get installed gh CLI version string (e.g. '2.101.0')."""
        try:
            res = GhCli.run(["version"], timeout=timeout)
            if res.returncode == 0 and res.stdout.strip():
                first_line = res.stdout.strip().splitlines()[0]
                parts = first_line.split()
                if len(parts) >= 3 and parts[0] == "gh" and parts[1] == "version":
                    return parts[2]
                return first_line
        except Exception:
            pass
        return None
