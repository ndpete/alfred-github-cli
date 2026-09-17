from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from src.cache import Cache
from src.gh import GhCli
from src.models import Feedback, Item, Modifier


def spawn_background_sync() -> None:
    """Spawn worker.py as a detached background process."""
    worker_script = Path(__file__).parent / "worker.py"
    try:
        subprocess.Popen(
            [sys.executable, str(worker_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        pass


def get_repo_icon(repo: dict[str, Any]) -> str:
    if repo.get("is_fork"):
        return "fork"
    if repo.get("is_private"):
        return "private-repo"
    return "repo"


def format_repo_item(repo: dict[str, Any]) -> Item:
    repo_id = repo["id"]
    desc = repo.get("description") or "No description"
    url = repo.get("url") or f"https://github.com/{repo_id}"
    stars = repo.get("stars", 0)
    star_str = f" ★ {stars}" if stars > 0 else ""

    item = Item(
        title=repo_id,
        subtitle=f"{desc}{star_str}",
        arg=url,
        autocomplete=f"{repo_id} ",
        uid=repo_id,
        icon=get_repo_icon(repo),
        valid=True,
    )

    # Cmd modifier: Jump straight to Pull Requests
    item.mods["cmd"] = Modifier(
        valid=True,
        arg=f"{url}/pulls",
        subtitle=f"Open Pull Requests for {repo_id}",
    )
    # Alt modifier: Jump straight to Issues
    item.mods["alt"] = Modifier(
        valid=True,
        arg=f"{url}/issues",
        subtitle=f"Open Issues for {repo_id}",
    )
    return item


def format_org_item(org: dict[str, Any]) -> Item:
    login = org["login"]
    name = org.get("name") or login
    url = org.get("url") or f"https://github.com/{login}"
    return Item(
        title=login,
        subtitle=f"Organization: {name}",
        arg=url,
        autocomplete=f"@{login} ",
        uid=f"org:{login}",
        icon="organization",
        valid=True,
    )


def handle_system_commands(fb: Feedback, query: str) -> None:
    sub = query.lstrip(">").strip().lower()
    commands = [
        ("refresh", "Force refresh cached repositories from GitHub", "cmd:refresh", "update"),
        ("auth", "Check GitHub CLI authentication status", "cmd:auth", "settings"),
        ("clear-cache", "Clear local SQLite database", "cmd:clear-cache", "logout"),
    ]
    for name, desc, arg, icon in commands:
        if not sub or sub in name:
            fb.add_item(
                Item(
                    title=f"> {name}",
                    subtitle=desc,
                    arg=arg,
                    icon=icon,
                    valid=True,
                )
            )


def handle_my_commands(fb: Feedback, query: str, cache: Cache) -> None:
    sub = query.removeprefix("my").strip().lower()

    my_items = [
        ("pulls", "View your Pull Requests", "https://github.com/pulls", "pull-request"),
        ("issues", "View your assigned Issues", "https://github.com/issues", "issue"),
        ("stars", "View your Starred Repositories", "https://github.com/stars", "stars"),
        ("notifications", "View GitHub Notifications", "https://github.com/notifications", "notifications"),
    ]

    if not sub:
        for name, desc, url, icon in my_items:
            fb.add_item(
                Item(
                    title=f"my {name}",
                    subtitle=desc,
                    arg=url,
                    autocomplete=f"my {name} ",
                    icon=icon,
                    valid=True,
                )
            )
        return

    # Subcommand filtering
    if sub.startswith("star"):
        starred = [r for r in cache.get_all_repos() if r.get("is_starred")]
        if starred:
            for r in starred[:25]:
                fb.add_item(format_repo_item(r))
        else:
            fb.add_item(
                Item(
                    title="No starred repos cached",
                    subtitle="Run '> refresh' to update cache",
                    arg="https://github.com/stars",
                    icon="stars",
                    valid=True,
                )
            )
        return

    for name, desc, url, icon in my_items:
        if sub in name:
            fb.add_item(
                Item(
                    title=f"my {name}",
                    subtitle=desc,
                    arg=url,
                    icon=icon,
                    valid=True,
                )
            )


def handle_repo_subcommands(fb: Feedback, repo_id: str, subquery: str) -> None:
    repo_url = f"https://github.com/{repo_id}"
    sub = subquery.strip().lower()

    sub_nav = [
        ("pulls", "Pull requests", f"{repo_url}/pulls", "pull-request"),
        ("issues", "Issues", f"{repo_url}/issues", "issue"),
        ("actions", "GitHub Actions workflows", f"{repo_url}/actions", "actions"),
        ("commits", "Commit history", f"{repo_url}/commits", "commits"),
        ("branches", "Branches", f"{repo_url}/branches", "branch"),
        ("releases", "Releases & tags", f"{repo_url}/releases", "releases"),
        ("discussions", "Discussions", f"{repo_url}/discussions", "discussions"),
        ("settings", "Repository settings", f"{repo_url}/settings", "settings"),
        ("wiki", "Wiki documentation", f"{repo_url}/wiki", "wiki"),
    ]

    matched = False
    for name, desc, url, icon in sub_nav:
        if not sub or sub in name:
            fb.add_item(
                Item(
                    title=f"{repo_id} {name}",
                    subtitle=desc,
                    arg=url,
                    icon=icon,
                    valid=True,
                )
            )
            matched = True

    if not matched or sub:
        # Provide in-repo search option
        fb.add_item(
            Item(
                title=f"Search '{repo_id}' for '{sub}'",
                subtitle=f"Open GitHub search within {repo_id}",
                arg=f"{repo_url}/search?q={sub}",
                icon="search",
                valid=True,
            )
        )


def run_search(query: str) -> Feedback:
    fb = Feedback()
    raw_query = query
    query = query.strip()

    cache = Cache()

    # 1. If cache is empty, check gh CLI installation, auth, and perform initial sync
    if not cache.has_repos():
        if not GhCli.is_installed():
            fb.add_item(
                Item(
                    title="GitHub CLI (gh) not found",
                    subtitle="Please install gh (e.g. brew install gh) to use this workflow",
                    arg="https://cli.github.com",
                    valid=True,
                    icon="settings",
                )
            )
            return fb

        if not GhCli.check_auth():
            fb.add_item(
                Item(
                    title="GitHub CLI not authenticated",
                    subtitle="Run 'gh auth login' in your terminal to authenticate",
                    arg="https://cli.github.com/manual/gh_auth_login",
                    valid=True,
                    icon="settings",
                )
            )
            return fb

        from src.worker import sync_github_data
        sync_github_data(cache)
    elif cache.is_sync_due(max_age_seconds=1800):
        spawn_background_sync()

    # 4. Handle System Commands ("> ...")
    if query.startswith(">"):
        handle_system_commands(fb, query)
        return fb

    # 5. Handle "my" Commands ("my pulls", "my issues", etc.)
    if query == "my" or raw_query.startswith("my "):
        handle_my_commands(fb, query, cache)
        return fb

    # 6. Handle Deep Repo Subcommands ("owner/repo ...")
    parts = raw_query.split(maxsplit=1)
    if len(parts) >= 1 and "/" in parts[0] and (len(parts) == 2 or raw_query.endswith(" ")):
        repo_id = parts[0]
        sub = parts[1] if len(parts) == 2 else ""
        handle_repo_subcommands(fb, repo_id, sub)
        return fb

    # 7. Handle User Filter ("@username")
    if query.startswith("@"):
        user = query.removeprefix("@").strip().lower()
        repos = [r for r in cache.get_all_repos() if user in r["owner"].lower()]
        for r in repos[:30]:
            fb.add_item(format_repo_item(r))
        if not repos:
            fb.add_item(
                Item(
                    title=f"Open GitHub profile for @{user}",
                    subtitle=f"https://github.com/{user}",
                    arg=f"https://github.com/{user}",
                    icon="user",
                    valid=True,
                )
            )
        return fb

    # 8. Handle Global Search ("s <query>")
    if query.startswith("s "):
        search_term = query[2:].strip()
        if search_term:
            fb.add_item(
                Item(
                    title=f"Search GitHub for '{search_term}'",
                    subtitle="Open global search on GitHub.com",
                    arg=f"https://github.com/search?q={search_term}",
                    icon="search",
                    valid=True,
                )
            )
            return fb

    # 9. Default Search: Repositories & Organizations
    repos = cache.search_repos(query, limit=30)
    for r in repos:
        fb.add_item(format_repo_item(r))

    # Also show matching orgs if query is short
    if query and len(query) <= 15:
        orgs = cache.search_orgs(query)
        for o in orgs[:5]:
            fb.add_item(format_org_item(o))

    # Fallback search item at bottom
    if query:
        fb.add_item(
            Item(
                title=f"Search GitHub for '{query}'",
                subtitle="Open search in browser",
                arg=f"https://github.com/search?q={query}",
                icon="search",
                valid=True,
            )
        )

    return fb


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else ""
    feedback = run_search(query)
    feedback.emit()


if __name__ == "__main__":
    main()
