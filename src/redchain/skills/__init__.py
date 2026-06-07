"""Reusable skill modules. Skills are invokable from any phase via the registry."""

from redchain.skills.base import Skill
from redchain.skills.recon_osint import ReconOsintSkill

SKILL_REGISTRY: dict[str, type[Skill]] = {
    "recon_osint": ReconOsintSkill,
}

__all__ = ["SKILL_REGISTRY", "Skill", "ReconOsintSkill"]
