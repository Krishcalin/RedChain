from __future__ import annotations

from pathlib import Path

from redchain.runtime.state import EngagementState, PhaseStatus


def test_initialize_creates_phases(engagement_dir: Path) -> None:
    with EngagementState(engagement_dir) as s:
        s.initialize(target="https://example.com", preset="webapp", phases=["scope", "recon", "report"])
        phases = s.phases()
    assert [p.name for p in phases] == ["scope", "recon", "report"]
    assert all(p.status == PhaseStatus.PENDING for p in phases)


def test_initialize_is_idempotent(engagement_dir: Path) -> None:
    with EngagementState(engagement_dir) as s:
        s.initialize(target="t", preset="webapp", phases=["scope"])
        s.initialize(target="t", preset="webapp", phases=["scope"])
        assert len(s.phases()) == 1


def test_next_pending_phase(engagement_dir: Path) -> None:
    with EngagementState(engagement_dir) as s:
        s.initialize(target="t", preset="webapp", phases=["scope", "recon"])
        assert s.next_pending_phase().name == "scope"
        s.mark_running("scope")
        s.mark_awaiting_gate("scope", Path("x"))
        s.record_gate_decision("scope", passed=True, reason="ok", artifact_path=Path("x"))
        assert s.next_pending_phase().name == "recon"


def test_failed_gate_keeps_phase_resumable(engagement_dir: Path) -> None:
    with EngagementState(engagement_dir) as s:
        s.initialize(target="t", preset="webapp", phases=["scope"])
        s.mark_running("scope")
        s.mark_awaiting_gate("scope", Path("x"))
        s.record_gate_decision("scope", passed=False, reason="missing section", artifact_path=Path("x"))
        record = s.next_pending_phase()
        assert record is not None
        assert record.name == "scope"
        assert record.status == PhaseStatus.FAILED_GATE
        assert record.gate_reason == "missing section"
