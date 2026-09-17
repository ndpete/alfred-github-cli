from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any

BUNDLE_ID = "com.github.ndpete.alfred-github-cli"


def get_data_dir() -> Path:
    """Return the workflow data directory, creating it if necessary."""
    env_dir = os.environ.get("alfred_workflow_data")
    if env_dir:
        path = Path(env_dir)
    else:
        path = Path.home() / "Library" / "Application Support" / "Alfred" / "Workflow Data" / BUNDLE_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    return get_data_dir() / "github.sqlite"


def is_subsequence(sub: str, target: str) -> bool:
    """Check if sub is a subsequence of target (characters appear in order)."""
    it = iter(target)
    return all(c in it for c in sub)


def score_repo(tokens: list[str], repo: dict[str, Any]) -> int:
    repo_id = repo["id"].lower()
    repo_name = repo["name"].lower()
    owner = repo["owner"].lower()
    desc = (repo.get("description") or "").lower()

    score = 0
    for token in tokens:
        # 1. Exact match on repo name or full ID
        if token == repo_name or token == repo_id:
            score += 500
        # 2. Token starts repo_name or appears after delimiter (- or _)
        elif repo_name.startswith(token) or f"-{token}" in repo_name or f"_{token}" in repo_name:
            score += 300
        # 3. Substring in repo name
        elif token in repo_name:
            score += 200
        # 4. Token matches owner or appears right after org slash
        elif token == owner or f"{token}/" in repo_id or f"/{token}" in repo_id:
            score += 150
        elif token in repo_id:
            score += 100
        # 5. Substring in description
        elif token in desc:
            score += 40
        # 6. Subsequence / abbreviation match on repo name (e.g. "ghc" -> "github-cli")
        elif is_subsequence(token, repo_name):
            score += 25
        # 7. Subsequence on full repo ID
        elif is_subsequence(token, repo_id):
            score += 15
        else:
            return 0

    # Starred bonus
    if repo.get("is_starred"):
        score += 20
    # Original (non-fork) bonus
    if not repo.get("is_fork"):
        score += 10

    return score


class Cache:
    """SQLite cache with WAL mode for sub-10ms Alfred queries."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or get_db_path()
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS repos (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    description TEXT,
                    url TEXT NOT NULL,
                    is_private INTEGER DEFAULT 0,
                    is_fork INTEGER DEFAULT 0,
                    stars INTEGER DEFAULT 0,
                    pushed_at TEXT,
                    is_starred INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_repos_name ON repos(name);
                CREATE INDEX IF NOT EXISTS idx_repos_owner ON repos(owner);
                CREATE INDEX IF NOT EXISTS idx_repos_pushed ON repos(pushed_at DESC);

                CREATE TABLE IF NOT EXISTS orgs (
                    login TEXT PRIMARY KEY,
                    name TEXT,
                    url TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at REAL
                );
                """
            )

    def set_meta(self, key: str, value: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO meta (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, value, time.time()),
            )

    def get_meta(self, key: str) -> str | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
            return str(row["value"]) if row else None

    def get_last_sync_time(self) -> float:
        with self._get_connection() as conn:
            row = conn.execute("SELECT updated_at FROM meta WHERE key = 'last_synced'").fetchone()
            if row and row["updated_at"]:
                return float(row["updated_at"])
            return 0.0

    def is_sync_due(self, max_age_seconds: float = 3600.0) -> bool:
        last = self.get_last_sync_time()
        return (time.time() - last) > max_age_seconds

    def has_repos(self) -> bool:
        with self._get_connection() as conn:
            row = conn.execute("SELECT COUNT(1) as cnt FROM repos").fetchone()
            return bool(row and row["cnt"] > 0)

    def upsert_repos(self, repos: list[dict[str, Any]]) -> None:
        if not repos:
            return
        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO repos (id, name, owner, description, url, is_private, is_fork, stars, pushed_at, is_starred)
                VALUES (:id, :name, :owner, :description, :url, :is_private, :is_fork, :stars, :pushed_at, :is_starred)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    owner=excluded.owner,
                    description=excluded.description,
                    url=excluded.url,
                    is_private=excluded.is_private,
                    is_fork=excluded.is_fork,
                    stars=excluded.stars,
                    pushed_at=excluded.pushed_at,
                    is_starred=excluded.is_starred
                """,
                repos,
            )

    def upsert_orgs(self, orgs: list[dict[str, Any]]) -> None:
        if not orgs:
            return
        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO orgs (login, name, url)
                VALUES (:login, :name, :url)
                ON CONFLICT(login) DO UPDATE SET
                    name=excluded.name,
                    url=excluded.url
                """,
                orgs,
            )

    def get_all_repos(self) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM repos ORDER BY pushed_at DESC").fetchall()
            return [dict(r) for r in rows]

    def get_all_orgs(self) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM orgs ORDER BY login ASC").fetchall()
            return [dict(r) for r in rows]

    def search_repos(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        query = query.strip()
        all_repos = self.get_all_repos()
        if not query:
            return all_repos[:limit]

        tokens = query.lower().split()
        scored: list[tuple[int, str, dict[str, Any]]] = []
        for r in all_repos:
            s = score_repo(tokens, r)
            if s > 0:
                pushed = r.get("pushed_at") or ""
                scored.append((s, pushed, r))

        # Sort primarily by score DESC, secondarily by pushed_at DESC
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [item[2] for item in scored[:limit]]

    def search_orgs(self, query: str) -> list[dict[str, Any]]:
        query = query.strip()
        with self._get_connection() as conn:
            if not query:
                rows = conn.execute("SELECT * FROM orgs ORDER BY login ASC").fetchall()
            else:
                pattern = f"%{query}%"
                rows = conn.execute(
                    "SELECT * FROM orgs WHERE login LIKE ? OR name LIKE ? ORDER BY login ASC",
                    (pattern, pattern),
                ).fetchall()
            return [dict(r) for r in rows]
