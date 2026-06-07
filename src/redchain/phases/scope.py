"""Scope phase — define engagement scope, objectives, constraints."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from redchain.agents.planner import Planner
from redchain.phases.base import Phase, PhaseContext, extract_json


class ScopeArtifactModel(BaseModel):
    target: str
    preset: str
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    authorization_notes: str = ""
    rules_of_engagement: list[str] = Field(default_factory=list)


class ScopePhase(Phase):
    name = "scope"
    artifact_filename = "scope_brief.md"
    template_name = "scope_brief.md.j2"

    def execute(self, ctx: PhaseContext) -> Path:
        planner = Planner(
            engagement_dir=ctx.engagement_dir,
            phase=self.name,
            dry_run=ctx.dry_run,
            fixture_dir=ctx.fixture_dir,
            model=ctx.model,
        )
        scope_hint = ctx.extras.get("scope_hint", "")
        user_prompt = (
            f"Target: {ctx.target}\n"
            f"Preset: {ctx.preset}\n"
            f"Operator-provided scope notes (may be empty): {scope_hint or '(none)'}\n\n"
            "Produce a scope brief as JSON with the following keys: "
            "`in_scope` (list of strings), `out_of_scope` (list of strings), "
            "`objectives` (list of strings), `constraints` (list of strings), "
            "`authorization_notes` (string), `rules_of_engagement` (list of strings). "
            "Return JSON only, wrapped in a ```json fenced block."
        )
        response = planner.run(prompt=user_prompt)
        ctx.state.record_transcript(
            phase=self.name, agent=planner.name,
            transcript_path=response.transcript_path or Path(),
            usage=response.usage,
        )
        data = extract_json(response.text)
        model = ScopeArtifactModel(target=ctx.target, preset=ctx.preset, **data)
        artifact_path = ctx.artifacts.render_and_write(
            self.template_name,
            self.artifact_filename,
            {"scope": model.model_dump()},
        )
        return artifact_path
