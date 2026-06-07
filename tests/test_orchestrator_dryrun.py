"""End-to-end dry-run test — the orchestrator runs the webapp preset to completion
using bundled fixtures, with no API calls."""

from __future__ import annotations

from pathlib import Path

from redchain.runtime.orchestrator import EngagementConfig, Orchestrator, load_preset


def test_webapp_preset_runs_end_to_end_in_dry_run(engagement_dir: Path) -> None:
    preset = load_preset("webapp")
    config = EngagementConfig(
        target="https://app.example.com",
        preset="webapp",
        phases=preset["phases"],
        out_dir=engagement_dir,
        dry_run=True,
    )
    with Orchestrator(config) as orch:
        ok = orch.run()
        summary = orch.summary()
    assert ok, summary
    statuses = {p["name"]: p["status"] for p in summary["phases"]}
    assert statuses == {"scope": "completed", "recon": "completed", "report": "completed"}
    for filename in ("scope_brief.md", "recon_dossier.md", "executive_report.md"):
        assert (engagement_dir / "artifacts" / filename).exists()
