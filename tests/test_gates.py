from __future__ import annotations

from pathlib import Path

from redchain.gates.recon_gate import ReconGate
from redchain.gates.report_gate import ReportGate
from redchain.gates.scope_gate import ScopeGate
from redchain.runtime.artifacts import ArtifactStore
from redchain.runtime.state import EngagementState
from redchain.phases.base import PhaseContext


def _ctx(engagement_dir: Path) -> PhaseContext:
    state = EngagementState(engagement_dir)
    return PhaseContext(
        phase_name="test",
        target="https://t",
        preset="webapp",
        engagement_dir=engagement_dir,
        artifacts=ArtifactStore(engagement_dir),
        state=state,
    )


def test_scope_gate_rejects_missing_sections(engagement_dir: Path) -> None:
    ctx = _ctx(engagement_dir)
    path = ctx.artifacts.write("scope_brief.md", "# brief\n")
    decision = ScopeGate().validate(ctx, path)
    assert not decision.passed
    assert "missing" in decision.reason


def test_scope_gate_rejects_empty_in_scope(engagement_dir: Path) -> None:
    ctx = _ctx(engagement_dir)
    body = (
        "# brief\n"
        "## In Scope\n- _(none)_\n"
        "## Objectives\n- get in\n"
        "## Authorization\nyes\n"
    )
    path = ctx.artifacts.write("scope_brief.md", body)
    decision = ScopeGate().validate(ctx, path)
    assert not decision.passed
    assert "In Scope" in decision.reason


def test_scope_gate_accepts_well_formed(engagement_dir: Path) -> None:
    ctx = _ctx(engagement_dir)
    body = (
        "# brief\n"
        "## In Scope\n- https://app.example.com\n"
        "## Objectives\n- find critical vulns\n"
        "## Authorization\nwritten authorization on file\n"
    )
    path = ctx.artifacts.write("scope_brief.md", body)
    decision = ScopeGate().validate(ctx, path)
    assert decision.passed


def test_recon_gate_rejects_no_entries(engagement_dir: Path) -> None:
    ctx = _ctx(engagement_dir)
    body = "# recon\n## Entrypoints\n- _(none)_\n## Services\n- _(none)_\n"
    path = ctx.artifacts.write("recon_dossier.md", body)
    decision = ReconGate().validate(ctx, path)
    assert not decision.passed


def test_recon_gate_accepts_with_entries(engagement_dir: Path) -> None:
    ctx = _ctx(engagement_dir)
    body = (
        "# recon\n"
        "## Entrypoints\n- **GET https://t/login** — auth\n"
        "## Services\n- _(none)_\n"
    )
    path = ctx.artifacts.write("recon_dossier.md", body)
    decision = ReconGate().validate(ctx, path)
    assert decision.passed


def test_report_gate_rejects_short_summary(engagement_dir: Path) -> None:
    ctx = _ctx(engagement_dir)
    body = (
        "# report\n"
        "## Executive Summary\n\nshort\n"
        "## Findings\n- a\n"
        "## Next Steps\n- b\n"
    )
    path = ctx.artifacts.write("executive_report.md", body)
    decision = ReportGate().validate(ctx, path)
    assert not decision.passed


def test_report_gate_accepts_well_formed(engagement_dir: Path) -> None:
    ctx = _ctx(engagement_dir)
    body = (
        "# report\n"
        "## Executive Summary\n\n"
        "The engagement ran end-to-end in dry-run mode and produced both "
        "a scope brief and a recon dossier for downstream analysis.\n"
        "## Findings\n- a\n"
        "## Next Steps\n- b\n"
    )
    path = ctx.artifacts.write("executive_report.md", body)
    decision = ReportGate().validate(ctx, path)
    assert decision.passed
