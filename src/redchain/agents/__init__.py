from redchain.agents.base import Agent
from redchain.agents.network_analyst import NetworkAnalyst
from redchain.agents.planner import Planner

AGENT_REGISTRY: dict[str, type[Agent]] = {
    "planner": Planner,
    "network_analyst": NetworkAnalyst,
}

__all__ = ["AGENT_REGISTRY", "Agent", "NetworkAnalyst", "Planner"]
