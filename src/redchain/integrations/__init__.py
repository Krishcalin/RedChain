"""Tool integration wrappers. Each integration runs an external tool and parses output."""

from redchain.integrations.base import Integration
from redchain.integrations.nmap import NmapIntegration

INTEGRATION_REGISTRY: dict[str, type[Integration]] = {
    "nmap": NmapIntegration,
}

__all__ = ["INTEGRATION_REGISTRY", "Integration", "NmapIntegration"]
