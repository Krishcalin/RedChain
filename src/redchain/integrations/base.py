"""Integration base — subprocess + parsing.

Integrations must:
  - Never inject unsanitized strings into the subprocess command.
  - Always accept and honor a ``timeout``.
  - Return a structured dict (or pydantic model) — never raw stdout.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Integration(ABC):
    name: str = ""

    @abstractmethod
    def run(self, *, target: str, timeout: int = 60, **kwargs: Any) -> dict[str, Any]:
        """Execute the integration and return parsed results."""
