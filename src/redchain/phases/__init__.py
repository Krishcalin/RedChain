"""Phase registry — map preset phase names to (Phase, Gate) pairs.

Stubs for the remaining six Kill Chain phases will be added here as they are
implemented. For v0.1.0, only scope/recon/report are wired end-to-end.
"""

from redchain.gates.recon_gate import ReconGate
from redchain.gates.report_gate import ReportGate
from redchain.gates.scope_gate import ScopeGate
from redchain.phases.base import Phase, PhaseContext, extract_json
from redchain.phases.recon import ReconPhase
from redchain.phases.report import ReportPhase
from redchain.phases.scope import ScopePhase

PHASE_REGISTRY: dict[str, tuple[type[Phase], type]] = {
    "scope": (ScopePhase, ScopeGate),
    "recon": (ReconPhase, ReconGate),
    "report": (ReportPhase, ReportGate),
}

__all__ = [
    "PHASE_REGISTRY",
    "Phase",
    "PhaseContext",
    "extract_json",
]
