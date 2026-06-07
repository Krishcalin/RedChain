"""Report phase — synthesize scope + recon into an executive deliverable."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from redchain.agents.planner import Planner
from redchain.phases.base import Phase, PhaseContext, extract_json


class Finding(BaseModel):
    title: str
    severity: str = "info"
    description: str
    evidence: str = ""
    recommendation: str = ""


class ReportArtifactModel(BaseModel):
    target: str
    executive_summary: str
    findings: list[Finding] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class ReportPhase(Phase):
    name = "report"
    artifact_filename = "executive_report.md"
    template_name = "executive_report.md.j2"

    def execute(self, ctx: PhaseContext) -> Path:
        scope_md = ctx.artifacts.read("scope_brief.md") or ""
        recon_md = ctx.artifacts.read("recon_dossier.md") or ""
        if not (scope_md and recon_md):
            raise RuntimeError(
                "report phase requires scope_brief.md and recon_dossier.md — "
                "run prior phases first"
            )
        planner = Planner(
            engagement_dir=ctx.engagement_dir,
            phase=self.name,
            dry_run=ctx.dry_run,
            fixture_dir=ctx.fixture_dir,
            model=ctx.model,
            agent_override="report_writer",
        )
        user_prompt = (
            f"Target: {ctx.target}\n\n"
            "=== SCOPE BRIEF ===\n"
            f"{scope_md}\n"
            "=== RECON DOSSIER ===\n"
            f"{recon_md}\n"
            "=====================\n\n"
            "Synthesize an executive report as JSON with keys: "
            "`executive_summary` (string, 3-6 sentences), "
            "`findings` (list of {title, severity, description, evidence, recommendation}), "
            "`next_steps` (list of strings — recommended phases to run next or remediation actions). "
            "Severity must be one of: critical, high, medium, low, info. "
            "Return JSON only, wrapped in a ```json fenced block."
        )
        response = planner.run(prompt=user_prompt)
        ctx.state.record_transcript(
            phase=self.name, agent=planner.name,
            transcript_path=response.transcript_path or Path(),
            usage=response.usage,
        )
        data = extract_json(response.text)
        model = ReportArtifactModel(target=ctx.target, **data)
        artifact_path = ctx.artifacts.render_and_write(
            self.template_name,
            self.artifact_filename,
            {"report": model.model_dump()},
        )
        return artifact_path
