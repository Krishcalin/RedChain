"""Recon phase — discover entrypoints, services, technologies, hosts."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from redchain.agents.network_analyst import NetworkAnalyst
from redchain.phases.base import Phase, PhaseContext, extract_json


class Entrypoint(BaseModel):
    url: str
    method: str = "GET"
    notes: str = ""


class ServiceFinding(BaseModel):
    host: str
    port: int | None = None
    service: str
    version: str | None = None
    notes: str = ""


class ReconArtifactModel(BaseModel):
    target: str
    summary: str = ""
    entrypoints: list[Entrypoint] = Field(default_factory=list)
    services: list[ServiceFinding] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    hosts: list[str] = Field(default_factory=list)
    leads: list[str] = Field(default_factory=list)


class ReconPhase(Phase):
    name = "recon"
    artifact_filename = "recon_dossier.md"
    template_name = "recon_dossier.md.j2"

    def execute(self, ctx: PhaseContext) -> Path:
        scope_md = ctx.artifacts.read("scope_brief.md") or ""
        if not scope_md:
            raise RuntimeError(
                "recon phase requires scope_brief.md to exist — run scope phase first"
            )
        analyst = NetworkAnalyst(
            engagement_dir=ctx.engagement_dir,
            phase=self.name,
            dry_run=ctx.dry_run,
            fixture_dir=ctx.fixture_dir,
            model=ctx.model,
        )
        user_prompt = (
            f"Target: {ctx.target}\n\n"
            "=== SCOPE BRIEF ===\n"
            f"{scope_md}\n"
            "===================\n\n"
            "Based on the scope above, produce a recon dossier as JSON with keys: "
            "`summary` (string), `entrypoints` (list of {url, method, notes}), "
            "`services` (list of {host, port, service, version, notes}), "
            "`technologies` (list of strings), `hosts` (list of strings), "
            "`leads` (list of strings — promising follow-ups for the next phase). "
            "Do NOT actually scan the target — propose what you would gather and "
            "document any safe passive findings the operator could verify. "
            "Return JSON only, wrapped in a ```json fenced block."
        )
        response = analyst.run(prompt=user_prompt)
        ctx.state.record_transcript(
            phase=self.name, agent=analyst.name,
            transcript_path=response.transcript_path or Path(),
            usage=response.usage,
        )
        data = extract_json(response.text)
        model = ReconArtifactModel(target=ctx.target, **data)
        artifact_path = ctx.artifacts.render_and_write(
            self.template_name,
            self.artifact_filename,
            {"recon": model.model_dump()},
        )
        return artifact_path
