from pathlib import Path

from src.cache import Cache


def test_cache_init_and_upsert(tmp_path: Path):
    db_file = tmp_path / "test.sqlite"
    cache = Cache(db_file)

    assert not cache.has_repos()

    # Insert repos
    repos = [
        {
            "id": "owner/repo1",
            "name": "repo1",
            "owner": "owner",
            "description": "First repo",
            "url": "https://github.com/owner/repo1",
            "is_private": 0,
            "is_fork": 0,
            "stars": 42,
            "pushed_at": "2026-01-01T00:00:00Z",
            "is_starred": 1,
        },
        {
            "id": "other/repo2",
            "name": "repo2",
            "owner": "other",
            "description": "Second repo",
            "url": "https://github.com/other/repo2",
            "is_private": 1,
            "is_fork": 1,
            "stars": 5,
            "pushed_at": "2026-01-02T00:00:00Z",
            "is_starred": 0,
        },
    ]
    cache.upsert_repos(repos)
    assert cache.has_repos()

    all_repos = cache.get_all_repos()
    assert len(all_repos) == 2

    # Test search
    res = cache.search_repos("repo1")
    assert len(res) == 1
    assert res[0]["id"] == "owner/repo1"

    # Test search description
    res_desc = cache.search_repos("Second")
    assert len(res_desc) == 1
    assert res_desc[0]["id"] == "other/repo2"


def test_cache_orgs_and_meta(tmp_path: Path):
    db_file = tmp_path / "test.sqlite"
    cache = Cache(db_file)

    orgs = [
        {"login": "my-org", "name": "My Org", "url": "https://github.com/my-org"},
    ]
    cache.upsert_orgs(orgs)

    all_orgs = cache.get_all_orgs()
    assert len(all_orgs) == 1
    assert all_orgs[0]["login"] == "my-org"

    # Meta
    cache.set_meta("test_key", "test_val")
    assert cache.get_meta("test_key") == "test_val"
