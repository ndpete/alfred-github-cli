from src.models import Feedback, Item, Modifier


def test_item_basic_serialization():
    item = Item(
        title="test/repo",
        subtitle="A test repo",
        arg="https://github.com/test/repo",
        autocomplete="test/repo ",
        icon="repo",
    )
    d = item.to_dict()
    assert d["title"] == "test/repo"
    assert d["subtitle"] == "A test repo"
    assert d["arg"] == "https://github.com/test/repo"
    assert d["autocomplete"] == "test/repo "
    assert d["valid"] is True
    assert d["icon"] == {"path": "icons/repo.png"}


def test_item_with_modifiers():
    item = Item(title="repo")
    item.mods["cmd"] = Modifier(
        valid=True,
        arg="https://github.com/repo/pulls",
        subtitle="Open PRs",
    )
    d = item.to_dict()
    assert "cmd" in d["mods"]
    assert d["mods"]["cmd"]["arg"] == "https://github.com/repo/pulls"
    assert d["mods"]["cmd"]["subtitle"] == "Open PRs"


def test_feedback_serialization():
    fb = Feedback()
    fb.add_item(Item(title="item1"))
    fb.add_item(Item(title="item2"))
    d = fb.to_dict()
    assert len(d["items"]) == 2
    assert d["items"][0]["title"] == "item1"
    assert d["items"][1]["title"] == "item2"
