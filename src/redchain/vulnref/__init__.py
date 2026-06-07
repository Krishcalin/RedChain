"""Vulnerability pattern reference library."""

import json
from importlib import resources
from typing import Any


def load_patterns() -> list[dict[str, Any]]:
    data = resources.files("redchain.vulnref").joinpath("patterns.json").read_text(encoding="utf-8")
    return json.loads(data)


def find_by_tag(tag: str) -> list[dict[str, Any]]:
    return [p for p in load_patterns() if tag in p.get("tags", [])]


__all__ = ["load_patterns", "find_by_tag"]
