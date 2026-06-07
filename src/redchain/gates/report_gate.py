"""Report gate — verifies the executive report has the mandated sections."""

from __future__ import annotations

from pathlib import Path

from typing import TYPE_CHECKING

from redchain.gates.base import Gate, GateDecision

if TYPE_CHECKING:
    from redchain.phases.base import PhaseContext


class ReportGate(Gate):
    name = "report_gate"

    REQUIRED_SECTIONS = (
        "## Executive Summary",
        "## Findings",
        "## Next Steps",
    )

    def validate(self, ctx: "PhaseContext", artifact_path: Path) -> GateDecision:
        if not artifact_path.exists():
            return GateDecision(False, f"artifact missing: {artifact_path}")
        content = artifact_path.read_text(encoding="utf-8")
        missing = [s for s in self.REQUIRED_SECTIONS if s not in content]
        if missing:
            return GateDecision(False, f"missing sections: {', '.join(missing)}")
        summary_body = self._section_body(content, "## Executive Summary").strip()
        if len(summary_body) < 60:
            return GateDecision(
                False,
                "Executive Summary is too short (<60 chars) — synthesize more from prior artifacts",
            )
        return GateDecision(True, "executive report complete")

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
