"""Phase base class and PhaseContext."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from redchain.runtime.artifacts import ArtifactStore
from redchain.runtime.state import EngagementState


@dataclass
class PhaseContext:
    phase_name: str
    target: str
    preset: str
    engagement_dir: Path
    artifacts: ArtifactStore
    state: EngagementState
    dry_run: bool = False
    fixture_dir: Path | None = None
    model: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


class Phase(ABC):
    """A single Kill Chain phase.

    Subclasses set:
      - ``name``: short phase identifier (matches preset entry).
      - ``artifact_filename``: name of the artifact under ``artifacts/``.
      - ``template_name``: Jinja2 template under ``redchain/templates/``.
    """

    name: str = ""
    artifact_filename: str = ""
    template_name: str = ""

    @abstractmethod
    def execute(self, ctx: PhaseContext) -> Path:
        """Run the phase and return the path to the rendered artifact."""


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)


def extract_json(text: str) -> Any:
    """Extract the first JSON object/array from agent text.

    Tolerates code-fenced blocks (```json ... ```) and raw JSON. Raises
    ``ValueError`` if no valid JSON can be located.
    """
    m = _JSON_FENCE_RE.search(text)
    if m:
        candidate = m.group(1)
    else:
        # Fallback: try the whole text, or the first { ... } / [ ... ] span.
        first_obj = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        candidate = first_obj.group(1) if first_obj else text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ValueError(f"could not parse JSON from agent response: {e}") from e
