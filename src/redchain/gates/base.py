"""Gate base class and decision type."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redchain.phases.base import PhaseContext


@dataclass
class GateDecision:
    passed: bool
    reason: str


class Gate(ABC):
    """A gate validates a phase's artifact and decides whether to advance."""

    name: str = ""

    @abstractmethod
    def validate(self, ctx: "PhaseContext", artifact_path: Path) -> GateDecision:
        ...
