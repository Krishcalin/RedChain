"""Recon gate — requires at least one entrypoint or service before advancing."""

from __future__ import annotations

import re
from pathlib import Path

from typing import TYPE_CHECKING

from redchain.gates.base import Gate, GateDecision

if TYPE_CHECKING:
    from redchain.phases.base import PhaseContext


class ReconGate(Gate):
    name = "recon_gate"

    def validate(self, ctx: "PhaseContext", artifact_path: Path) -> GateDecision:
        if not artifact_path.exists():
            return GateDecision(False, f"artifact missing: {artifact_path}")
        content = artifact_path.read_text(encoding="utf-8")
        if "## Entrypoints" not in content or "## Services" not in content:
            return GateDecision(False, "missing Entrypoints or Services section")
        entrypoints = self._count_rows(content, "## Entrypoints")
        services = self._count_rows(content, "## Services")
        if entrypoints == 0 and services == 0:
            return GateDecision(
                False,
                "recon dossier lists no entrypoints and no services — "
                "weaponization will have nothing to work with",
            )
        return GateDecision(
            True,
            f"recon dossier valid ({entrypoints} entrypoints, {services} services)",
        )

    @staticmethod
    def _count_rows(content: str, heading: str) -> int:
        body = ReconGate._section_body(content, heading)
        # Count markdown list items OR table rows (anything that starts with "- " or "| ")
        count = 0
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and stripped not in {"- _(none)_", "- (none)"}:
                count += 1
            elif re.match(r"\|\s*[^-|\s]", stripped) and "---" not in stripped:
                # table data row (not separator); skip header
                count += 1
        # Subtract 1 for the header row if a table was used (heuristic: at least 2 rows means header + sep + data)
        if count >= 2 and "|" in body:
            count = max(0, count - 1)
        return count

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
