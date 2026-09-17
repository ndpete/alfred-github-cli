from __future__ import annotations

import argparse
import sys
import time
from typing import Any

from src.cache import Cache
from src.gh import GhCli

GRAPHQL_SYNC_QUERY = """
query {
  viewer {
    login
    name
    organizations(first: 50) {
      nodes {
        login
        name
        url
      }
    }
    repositories(first: 100, affiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER], orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        nameWithOwner
        name
        description
        url
        isPrivate
        isFork
        stargazerCount
        pushedAt
        owner {
          login
        }
      }
    }
    starredRepositories(first: 100, orderBy: {field: STARRED_AT, direction: DESC}) {
      nodes {
        nameWithOwner
        name
        description
        url
        isPrivate
        isFork
        stargazerCount
        pushedAt
        owner {
          login
        }
      }
    }
  }
}
"""


def sync_github_data(cache: Cache) -> bool:
    """Fetch user repos, orgs, and starred repos via GraphQL and store into SQLite."""
    if not GhCli.is_installed() or not GhCli.check_auth():
        return False

    data = GhCli.run_graphql(GRAPHQL_SYNC_QUERY)
    if not data or "viewer" not in data:
        return False

    viewer = data["viewer"]
    cache.set_meta("viewer_login", viewer.get("login", ""))
    cache.set_meta("viewer_name", viewer.get("name") or "")

    # Save organizations
    orgs: list[dict[str, Any]] = []
    if "organizations" in viewer and "nodes" in viewer["organizations"]:
        for o in viewer["organizations"]["nodes"]:
            orgs.append({
                "login": o["login"],
                "name": o.get("name") or o["login"],
                "url": o.get("url") or f"https://github.com/{o['login']}",
            })
    cache.upsert_orgs(orgs)

    # Save user repositories
    repos_map: dict[str, dict[str, Any]] = {}
    if "repositories" in viewer and "nodes" in viewer["repositories"]:
        for r in viewer["repositories"]["nodes"]:
            repo_id = r["nameWithOwner"]
            owner_login = r.get("owner", {}).get("login", repo_id.split("/")[0])
            repos_map[repo_id] = {
                "id": repo_id,
                "name": r["name"],
                "owner": owner_login,
                "description": r.get("description") or "",
                "url": r["url"],
                "is_private": 1 if r.get("isPrivate") else 0,
                "is_fork": 1 if r.get("isFork") else 0,
                "stars": r.get("stargazerCount", 0),
                "pushed_at": r.get("pushedAt") or "",
                "is_starred": 0,
            }

    # Save starred repositories
    if "starredRepositories" in viewer and "nodes" in viewer["starredRepositories"]:
        for r in viewer["starredRepositories"]["nodes"]:
            repo_id = r["nameWithOwner"]
            owner_login = r.get("owner", {}).get("login", repo_id.split("/")[0])
            if repo_id in repos_map:
                repos_map[repo_id]["is_starred"] = 1
            else:
                repos_map[repo_id] = {
                    "id": repo_id,
                    "name": r["name"],
                    "owner": owner_login,
                    "description": r.get("description") or "",
                    "url": r["url"],
                    "is_private": 1 if r.get("isPrivate") else 0,
                    "is_fork": 1 if r.get("isFork") else 0,
                    "stars": r.get("stargazerCount", 0),
                    "pushed_at": r.get("pushedAt") or "",
                    "is_starred": 1,
                }

    cache.upsert_repos(list(repos_map.values()))
    cache.set_meta("last_synced", str(time.time()))
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync GitHub data to local SQLite cache")
    parser.add_argument("--force", action="store_true", help="Force sync regardless of cache age")
    args = parser.parse_args()

    cache = Cache()
    if args.force or cache.is_sync_due():
        success = sync_github_data(cache)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
