from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Modifier:
    valid: bool = True
    arg: str = ""
    subtitle: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "arg": self.arg,
            "subtitle": self.subtitle,
        }


@dataclass
class Item:
    title: str
    subtitle: str = ""
    arg: str = ""
    autocomplete: str | None = None
    valid: bool = True
    icon: str | None = None
    uid: str | None = None
    match: str | None = None
    quicklookurl: str | None = None
    mods: dict[str, Modifier] = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        item: dict[str, Any] = {
            "title": self.title,
            "subtitle": self.subtitle,
            "arg": self.arg,
            "valid": self.valid,
        }
        if self.autocomplete is not None:
            item["autocomplete"] = self.autocomplete
        if self.icon:
            # If icon is a filename like 'repo' or 'repo.png'
            icon_path = self.icon if self.icon.endswith(".png") or "/" in self.icon else f"icons/{self.icon}.png"
            item["icon"] = {"path": icon_path}
        if self.uid:
            item["uid"] = self.uid
        if self.match:
            item["match"] = self.match
        if self.quicklookurl:
            item["quicklookurl"] = self.quicklookurl
        if self.mods:
            item["mods"] = {k: v.to_dict() for k, v in self.mods.items()}
        if self.variables:
            item["variables"] = self.variables
        return item


@dataclass
class Feedback:
    items: list[Item] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)

    def add_item(self, item: Item) -> Item:
        self.items.append(item)
        return item

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {
            "items": [item.to_dict() for item in self.items]
        }
        if self.variables:
            res["variables"] = self.variables
        return res

    def emit(self) -> None:
        json.dump(self.to_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        sys.stdout.flush()
