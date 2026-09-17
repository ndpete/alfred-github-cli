import pytest

from src.cache import Cache
from src.gh import GhCli
from src.search import run_search


@pytest.fixture(autouse=True)
def mock_gh_auth(monkeypatch, tmp_path):
    # Ensure cache has at least one repo and GhCli reports installed/authed
    monkeypatch.setattr(GhCli, "is_installed", staticmethod(lambda: True))
    monkeypatch.setattr(GhCli, "check_auth", staticmethod(lambda: True))
    db_file = tmp_path / "test.sqlite"
    cache = Cache(db_file)
    cache.upsert_repos([{
        "id": "owner/repo",
        "name": "repo",
        "owner": "owner",
        "description": "Mock repo",
        "url": "https://github.com/owner/repo",
        "is_private": 0,
        "is_fork": 0,
        "stars": 1,
        "pushed_at": "2026-01-01T00:00:00Z",
        "is_starred": 0,
    }])
    monkeypatch.setattr("src.search.Cache", lambda: cache)
    yield


def test_system_commands():
    fb = run_search("> refresh")
    items = fb.to_dict()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "> refresh"
    assert items[0]["arg"] == "cmd:refresh"

    fb_ver = run_search("> version")
    items_ver = fb_ver.to_dict()["items"]
    assert len(items_ver) == 1
    assert items_ver[0]["title"] == "> version"
    assert items_ver[0]["arg"] == "cmd:version"

    fb_auth = run_search("> auth")
    items_auth = fb_auth.to_dict()["items"]
    assert len(items_auth) == 1
    assert items_auth[0]["title"] == "> auth"
    assert items_auth[0]["arg"] == "cmd:auth"


def test_my_commands():
    fb = run_search("my ")
    items = fb.to_dict()["items"]
    titles = [i["title"] for i in items]
    assert "my pulls" in titles
    assert "my issues" in titles
    assert "my stars" in titles


def test_repo_subcommands():
    fb = run_search("owner/repo ")
    items = fb.to_dict()["items"]
    titles = [i["title"] for i in items]
    assert "owner/repo pulls" in titles
    assert "owner/repo issues" in titles
    assert "owner/repo actions" in titles
    assert "owner/repo commits" in titles


def test_empty_cache_shows_building_banner(monkeypatch, tmp_path):
    empty_db = tmp_path / "empty.sqlite"
    empty_cache = Cache(empty_db)
    monkeypatch.setattr("src.search.Cache", lambda: empty_cache)
    monkeypatch.setattr("src.search.spawn_background_sync", lambda: None)

    fb = run_search("test")
    items = fb.to_dict()["items"]
    assert items[0]["title"] == "Building initial repository cache..."
    assert items[0]["valid"] is False
    assert items[1]["title"] == "Search GitHub for 'test'"

