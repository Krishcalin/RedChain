"""Recon OSINT skill — stub.

In a real engagement, this skill would query passive OSINT sources (Shodan,
Censys, crt.sh, VirusTotal, etc.) and return a structured summary. For v0.1.0
it returns a placeholder, leaving the live integrations to future work.
"""

from __future__ import annotations

from typing import Any

from redchain.skills.base import Skill


class ReconOsintSkill(Skill):
    name = "recon_osint"
    description = "Passive OSINT lookup for a target (stub — no live calls in v0.1.0)."

    def run(self, *, target: str, **kwargs: Any) -> dict[str, Any]:
        return {
            "target": target,
            "sources_queried": [],
            "subdomains": [],
            "certificates": [],
            "open_ports_passive": [],
            "notes": (
                "ReconOsintSkill is a stub in v0.1.0. Wire concrete OSINT "
                "providers (crt.sh, Shodan, Censys, etc.) before using in a "
                "live engagement."
            ),
        }
