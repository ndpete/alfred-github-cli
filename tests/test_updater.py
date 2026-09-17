
from src.cache import Cache
from src.search import run_search
from src.updater import (
    check_for_updates,
    get_current_version,
    is_newer_version,
    parse_version,
)


def test_parse_version():
    assert parse_version("0.2.0") == (0, 2, 0)
    assert parse_version("v1.5.12") == (1, 5, 12)
    assert parse_version("v0.3.0-rc1") == (0, 3, 0)
    assert parse_version("2") == (2,)


def test_is_newer_version():
    assert is_newer_version("0.3.0", "0.2.0") is True
    assert is_newer_version("1.0.0", "0.9.9") is True
    assert is_newer_version("0.2.0", "0.2.0") is False
    assert is_newer_version("0.1.9", "0.2.0") is False
    assert is_newer_version("v0.3.0", "0.2.0") is True


def test_get_current_version():
    ver = get_current_version()
    assert isinstance(ver, str)
    assert len(ver.split(".")) >= 2


def test_check_for_updates_found(monkeypatch, tmp_path):
    cache = Cache(tmp_path / "test.sqlite")
    mock_release = {
        "tag_name": "v0.9.0",
        "html_url": "https://github.com/ndpete/alfred-github-cli/releases/tag/v0.9.0",
        "assets": [
            {
                "name": "alfred-github-cli.alfredworkflow",
                "browser_download_url": "https://example.com/dl.alfredworkflow",
            }
        ],
    }
    monkeypatch.setattr("src.updater.fetch_latest_release", lambda: mock_release)
    monkeypatch.setattr("src.updater.get_current_version", lambda: "0.2.0")

    info = check_for_updates(cache, force=True)
    assert info is not None
    assert info["version"] == "0.9.0"
    assert info["download_url"] == "https://example.com/dl.alfredworkflow"
    assert cache.get_meta("latest_version") == "0.9.0"


def test_check_for_updates_already_latest(monkeypatch, tmp_path):
    cache = Cache(tmp_path / "test.sqlite")
    mock_release = {
        "tag_name": "v0.2.0",
        "html_url": "https://github.com/ndpete/alfred-github-cli/releases/tag/v0.2.0",
        "assets": [],
    }
    monkeypatch.setattr("src.updater.fetch_latest_release", lambda: mock_release)
    monkeypatch.setattr("src.updater.get_current_version", lambda: "0.2.0")

    info = check_for_updates(cache, force=True)
    assert info is None
    assert cache.get_meta("latest_version") == ""


def test_update_banner_and_command(monkeypatch, tmp_path):
    cache = Cache(tmp_path / "test.sqlite")
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
    cache.set_meta("latest_version", "9.9.9")
    cache.set_meta("latest_download_url", "https://example.com/dl")

    monkeypatch.setattr("src.search.Cache", lambda: cache)
    monkeypatch.setattr("src.search.get_current_version", lambda: "0.2.0")

    # 1. Empty query should show update banner at top
    fb = run_search("")
    items = fb.to_dict()["items"]
    assert items[0]["title"] == "Update Available: v9.9.9"
    assert items[0]["arg"] == "cmd:update"

    # 2. System command list should include > update
    fb_sys = run_search(">")
    sys_items = fb_sys.to_dict()["items"]
    sys_titles = [i["title"] for i in sys_items]
    assert "> update" in sys_titles
    assert "> check-update" in sys_titles
