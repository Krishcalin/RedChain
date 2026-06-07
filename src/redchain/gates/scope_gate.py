"""Scope gate — verifies the scope brief is usable for downstream phases."""

from __future__ import annotations

from pathlib import Path

from typing import TYPE_CHECKING

from redchain.gates.base import Gate, GateDecision

if TYPE_CHECKING:
    from redchain.phases.base import PhaseContext


class ScopeGate(Gate):
    name = "scope_gate"

    REQUIRED_SECTIONS = (
        "## In Scope",
        "## Objectives",
        "## Authorization",
    )

    def validate(self, ctx: "PhaseContext", artifact_path: Path) -> GateDecision:
        if not artifact_path.exists():
            return GateDecision(False, f"artifact missing: {artifact_path}")
        content = artifact_path.read_text(encoding="utf-8")
        missing = [s for s in self.REQUIRED_SECTIONS if s not in content]
        if missing:
            return GateDecision(False, f"missing sections: {', '.join(missing)}")
        if self._section_is_effectively_empty(content, "## In Scope"):
            return GateDecision(False, "In Scope section is empty — no targets defined")
        if self._section_is_effectively_empty(content, "## Objectives"):
            return GateDecision(False, "Objectives section is empty — engagement has no goal")
        return GateDecision(True, "scope brief complete")

    @staticmethod
    def _section_is_effectively_empty(content: str, heading: str) -> bool:
        body = ScopeGate._section_body(content, heading)
        placeholders = {"_(none)_", "(none)", "-", "- _(none)_", "- (none)"}
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped in placeholders:
                continue
            # Treat list items whose content is only a placeholder as empty.
            if stripped.startswith("- ") and stripped[2:].strip() in {"_(none)_", "(none)", ""}:
                continue
            return False
        return True

    @staticmethod
    def _section_body(content: str, heading: str) -> str:
        lines = content.splitlines()
        try:
            start = lines.index(heading) + 1
        except ValueError:
            return ""
        body: list[str] = []
        for line in lines[start:]:
            if line.startswith("## "):
                break
            body.append(line)
        return "\n".join(body)
