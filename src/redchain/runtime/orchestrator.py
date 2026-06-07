"""Orchestrator — drives phase transitions for one engagement."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from redchain.phases import PHASE_REGISTRY, PhaseContext
from redchain.runtime.artifacts import ArtifactStore
from redchain.runtime.state import EngagementState, PhaseStatus


@dataclass
class EngagementConfig:
    target: str
    preset: str
    phases: list[str]
    out_dir: Path
    dry_run: bool = False
    fixture_dir: Path | None = None
    model: str | None = None
    extras: dict | None = None


class Orchestrator:
    """Iterates through preset.phases, invoking phases and their gates."""

    def __init__(self, config: EngagementConfig, *, console: Console | None = None):
        self.config = config
        self.console = console or Console()
        self.state = EngagementState(config.out_dir)
        self.artifacts = ArtifactStore(config.out_dir)
        self.state.initialize(
            target=config.target,
            preset=config.preset,
            phases=config.phases,
        )

    def close(self) -> None:
        self.state.close()

    def __enter__(self) -> "Orchestrator":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def run(self) -> bool:
        """Run all pending phases. Returns True if the engagement completed."""
        while True:
            record = self.state.next_pending_phase()
            if record is None:
                self.console.print("[green]All phases completed.[/green]")
                return True
            if record.name not in PHASE_REGISTRY:
                self.console.print(
                    f"[red]Unknown phase '{record.name}' in preset; aborting.[/red]"
                )
                return False
            phase_cls, gate_cls = PHASE_REGISTRY[record.name]
            self.console.print(f"[bold cyan]>> phase: {record.name}[/bold cyan]")
            self.state.mark_running(record.name)
            context = PhaseContext(
                phase_name=record.name,
                target=self.config.target,
                preset=self.config.preset,
                engagement_dir=self.config.out_dir,
                artifacts=self.artifacts,
                state=self.state,
                dry_run=self.config.dry_run,
                fixture_dir=self.config.fixture_dir,
                model=self.config.model,
                extras=self.config.extras or {},
            )
            phase = phase_cls()
            try:
                artifact_path = phase.execute(context)
            except Exception as e:
                self.console.print(f"[red]Phase {record.name} raised: {e}[/red]")
                self.state.record_gate_decision(
                    record.name, passed=False, reason=f"exception: {e}", artifact_path=None
                )
                return False
            self.state.mark_awaiting_gate(record.name, artifact_path)
            gate = gate_cls()
            decision = gate.validate(context, artifact_path)
            self.state.record_gate_decision(
                record.name,
                passed=decision.passed,
                reason=decision.reason,
                artifact_path=artifact_path,
            )
            if not decision.passed:
                self.console.print(
                    f"[yellow]Gate failed for {record.name}: {decision.reason}[/yellow]"
                )
                self.console.print(
                    "Fix the artifact at "
                    f"{artifact_path} and run `redchain resume {self.config.out_dir}`."
                )
                return False
            self.console.print(
                f"[green]OK[/green] {record.name} -> {artifact_path.name}"
            )
        # unreachable

    def summary(self) -> dict:
        return self.state.summary()


def load_preset(name: str) -> dict:
    """Load a preset YAML by name from the bundled presets package."""
    from importlib import resources

    import yaml

    presets_pkg = resources.files("redchain.presets")
    target = presets_pkg / f"{name}.yaml"
    if not target.is_file():
        available = sorted(
            p.name.removesuffix(".yaml")
            for p in presets_pkg.iterdir()
            if p.name.endswith(".yaml")
        )
        raise FileNotFoundError(
            f"unknown preset '{name}'. Available: {', '.join(available) or '(none)'}"
        )
    return yaml.safe_load(target.read_text(encoding="utf-8"))


def list_presets() -> list[str]:
    from importlib import resources

    presets_pkg = resources.files("redchain.presets")
    return sorted(
        p.name.removesuffix(".yaml")
        for p in presets_pkg.iterdir()
        if p.name.endswith(".yaml")
    )
