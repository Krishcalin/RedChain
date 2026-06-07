"""Skill base class. Skills are reusable helpers invokable from any phase."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Skill(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, *, target: str, **kwargs: Any) -> dict[str, Any]:
        """Execute the skill and return a structured result dict."""
