from src.search import run_search


def test_system_commands():
    fb = run_search("> refresh")
    items = fb.to_dict()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "> refresh"
    assert items[0]["arg"] == "cmd:refresh"


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
