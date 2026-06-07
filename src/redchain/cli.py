"""RedChain CLI.

Commands
--------
- ``redchain engage``       — start a new engagement
- ``redchain resume``       — resume a paused engagement (re-runs gate-failed and pending phases)
- ``redchain status``       — print engagement status as JSON
- ``redchain list-presets`` — list bundled presets
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from redchain import __version__
from redchain.runtime.orchestrator import EngagementConfig, Orchestrator, list_presets, load_preset

app = typer.Typer(
    name="redchain",
    no_args_is_help=True,
    help="Gated, multi-agent red-team engagement orchestrator.",
    add_completion=False,
)
console = Console()


@app.command()
def version() -> None:
    """Print RedChain version."""
    console.print(f"redchain {__version__}")


@app.command("list-presets")
def cmd_list_presets() -> None:
    """List bundled engagement presets."""
    presets = list_presets()
    if not presets:
        console.print("[yellow]no presets bundled[/yellow]")
        return
    table = Table(title="RedChain Presets")
    table.add_column("name", style="cyan")
    table.add_column("phases", style="white")
    table.add_column("description", style="dim")
    for name in presets:
        data = load_preset(name)
        table.add_row(
            name,
            " -> ".join(data.get("phases", [])),
            data.get("description", ""),
        )
    console.print(table)


@app.command()
def engage(
    preset: str = typer.Option(..., "--preset", "-p", help="Preset name (see list-presets)"),
    target: str = typer.Option(..., "--target", "-t", help="Target identifier (URL, host, IP)"),
    out: Path = typer.Option(..., "--out", "-o", help="Engagement output directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Use canned fixture responses; no API calls"),
    model: Optional[str] = typer.Option(None, "--model", help="Override Anthropic model id"),
    scope_hint: Optional[str] = typer.Option(
        None, "--scope-hint", help="Free-form operator notes passed to the Planner during scope phase"
    ),
    fixture_dir: Optional[Path] = typer.Option(
        None, "--fixture-dir", help="Override fixture directory for --dry-run"
    ),
) -> None:
    """Start a new engagement."""
    preset_data = load_preset(preset)
    phases = preset_data.get("phases", [])
    if not phases:
        console.print(f"[red]preset '{preset}' has no phases[/red]")
        raise typer.Exit(code=1)
    out = out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "preset": preset,
                "target": target,
                "phases": phases,
                "dry_run": dry_run,
                "model": model or preset_data.get("defaults", {}).get("model"),
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    config = EngagementConfig(
        target=target,
        preset=preset,
        phases=phases,
        out_dir=out,
        dry_run=dry_run,
        fixture_dir=fixture_dir,
        model=model or preset_data.get("defaults", {}).get("model"),
        extras={"scope_hint": scope_hint or ""},
    )
    with Orchestrator(config, console=console) as orch:
        ok = orch.run()
    raise typer.Exit(code=0 if ok else 2)


@app.command()
def resume(
    engagement_dir: Path = typer.Argument(..., help="Engagement directory created by `engage`"),
    dry_run: Optional[bool] = typer.Option(
        None, "--dry-run/--no-dry-run", help="Override manifest's dry-run setting"
    ),
) -> None:
    """Resume a paused engagement from disk."""
    engagement_dir = engagement_dir.expanduser().resolve()
    manifest_path = engagement_dir / "manifest.yaml"
    if not manifest_path.exists():
        console.print(f"[red]no manifest.yaml found at {manifest_path}[/red]")
        raise typer.Exit(code=1)
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    config = EngagementConfig(
        target=manifest["target"],
        preset=manifest["preset"],
        phases=manifest["phases"],
        out_dir=engagement_dir,
        dry_run=manifest.get("dry_run", False) if dry_run is None else dry_run,
        model=manifest.get("model"),
        extras={},
    )
    with Orchestrator(config, console=console) as orch:
        ok = orch.run()
    raise typer.Exit(code=0 if ok else 2)


@app.command()
def status(
    engagement_dir: Path = typer.Argument(..., help="Engagement directory"),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
) -> None:
    """Print engagement status."""
    from redchain.runtime.state import EngagementState

    engagement_dir = engagement_dir.expanduser().resolve()
    if not (engagement_dir / "state.sqlite").exists():
        console.print(f"[red]no state.sqlite at {engagement_dir}[/red]")
        raise typer.Exit(code=1)
    with EngagementState(engagement_dir) as state:
        summary = state.summary()
    if as_json:
        console.print_json(json.dumps(summary))
        return
    meta = summary["metadata"]
    console.print(f"[bold]Engagement[/bold] {engagement_dir}")
    console.print(f"  target  : {meta.get('target')}")
    console.print(f"  preset  : {meta.get('preset')}")
    console.print(f"  created : {meta.get('created_at')}")
    table = Table(title="Phases")
    table.add_column("phase", style="cyan")
    table.add_column("status")
    table.add_column("artifact", style="dim")
    table.add_column("gate", style="yellow")
    for p in summary["phases"]:
        status_text = p["status"]
        color = {
            "completed": "[green]completed[/green]",
            "failed_gate": "[red]failed_gate[/red]",
            "awaiting_gate": "[yellow]awaiting_gate[/yellow]",
            "running": "[cyan]running[/cyan]",
            "pending": "pending",
        }.get(status_text, status_text)
        table.add_row(p["name"], color, p.get("artifact") or "-", p.get("gate_reason") or "-")
    console.print(table)


if __name__ == "__main__":
    app()
