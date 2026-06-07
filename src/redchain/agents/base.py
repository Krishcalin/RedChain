"""Agent base class.

A specialist agent is a small wrapper around an :class:`AgentSession`. It owns
a system prompt and a name for transcript labeling. Phases instantiate agents
on demand and call ``run(prompt=...)``.
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path

from redchain.runtime.agent_session import AgentResponse, AgentSession


class Agent(ABC):
    name: str = "agent"
    system_prompt: str = ""

    def __init__(
        self,
        *,
        engagement_dir: Path,
        phase: str,
        dry_run: bool = False,
        fixture_dir: Path | None = None,
        model: str | None = None,
        agent_override: str | None = None,
    ):
        self._session = AgentSession(
            engagement_dir=engagement_dir,
            phase=phase,
            agent=agent_override or self.name,
            model=model,
            dry_run=dry_run,
            fixture_dir=fixture_dir,
        )
        self._agent_label = agent_override or self.name

    @property
    def label(self) -> str:
        return self._agent_label

    def run(self, *, prompt: str, max_tokens: int = 4096) -> AgentResponse:
        messages = [{"role": "user", "content": prompt}]
        return self._session.invoke(
            system=self.system_prompt,
            messages=messages,
            max_tokens=max_tokens,
        )
