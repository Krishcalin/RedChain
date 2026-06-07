"""Anthropic client wrapper with dry-run support and transcript persistence.

Every agent run goes through ``AgentSession.invoke()``. In dry-run mode the
session loads canned responses from ``tests/fixtures/`` (or a user-supplied
fixture dir) so the orchestrator can run end-to-end without an API key.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class AgentResponse:
    text: str
    raw: dict[str, Any]
    usage: dict[str, int] = field(default_factory=dict)
    transcript_path: Path | None = None


class AgentSession:
    """Thin Anthropic wrapper.

    Construct one session per agent invocation. The session writes a JSONL
    transcript to ``<engagement_dir>/transcripts/<phase>-<agent>-<ts>.jsonl``
    and returns an :class:`AgentResponse` with usage metadata for the orchestrator.

    Parameters
    ----------
    engagement_dir
        Root engagement directory. Transcripts are written under ``transcripts/``.
    phase
        Phase name (used in transcript filename).
    agent
        Agent name (used in transcript filename).
    model
        Anthropic model id. Defaults to the latest Sonnet.
    dry_run
        If True, no API call is made. Canned responses are loaded from ``fixture_dir``.
    fixture_dir
        Directory containing ``<agent>.json`` fixture files for dry-run mode.
    """

    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(
        self,
        engagement_dir: Path,
        *,
        phase: str,
        agent: str,
        model: str | None = None,
        dry_run: bool = False,
        fixture_dir: Path | None = None,
    ):
        self.engagement_dir = engagement_dir
        self.phase = phase
        self.agent = agent
        self.model = model or self.DEFAULT_MODEL
        self.dry_run = dry_run
        self.fixture_dir = fixture_dir
        self.transcripts_dir = engagement_dir / "transcripts"
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)

    def _transcript_path(self) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return self.transcripts_dir / f"{self.phase}-{self.agent}-{ts}.jsonl"

    def _write_transcript(self, records: list[dict]) -> Path:
        path = self._transcript_path()
        with path.open("w", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return path

    def invoke(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.2,
        cache_system: bool = True,
    ) -> AgentResponse:
        if self.dry_run:
            return self._invoke_dry_run(system=system, messages=messages)

        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as e:  # pragma: no cover - import guard
            raise RuntimeError(
                "anthropic SDK is required for live runs. Install with `pip install anthropic` "
                "or use --dry-run."
            ) from e

        client = anthropic.Anthropic()
        system_payload: Any = system
        if cache_system and system:
            system_payload = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        response = client.messages.create(
            model=self.model,
            system=system_payload,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text_chunks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        text = "".join(text_chunks)
        usage = {
            "input_tokens": getattr(response.usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(response.usage, "output_tokens", 0) or 0,
            "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            "cache_creation_input_tokens": getattr(
                response.usage, "cache_creation_input_tokens", 0
            ) or 0,
        }
        transcript_path = self._write_transcript(
            [
                {"role": "system", "content": system, "model": self.model},
                *messages,
                {"role": "assistant", "content": text, "usage": usage},
            ]
        )
        return AgentResponse(text=text, raw=response.model_dump(), usage=usage, transcript_path=transcript_path)

    def _invoke_dry_run(self, *, system: str, messages: list[dict]) -> AgentResponse:
        fixture_dir = self.fixture_dir or self._default_fixture_dir()
        fixture_path = fixture_dir / f"{self.agent}.json"
        if not fixture_path.exists():
            raise FileNotFoundError(
                f"dry-run mode requires a fixture for agent '{self.agent}' at {fixture_path}"
            )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        text = fixture.get("text") or json.dumps(fixture)
        usage = {"input_tokens": 0, "output_tokens": 0,
                 "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
        transcript_path = self._write_transcript(
            [
                {"role": "system", "content": system, "model": "dry-run"},
                *messages,
                {"role": "assistant", "content": text, "usage": usage, "dry_run": True},
            ]
        )
        return AgentResponse(text=text, raw=fixture, usage=usage, transcript_path=transcript_path)

    @staticmethod
    def _default_fixture_dir() -> Path:
        env_dir = os.environ.get("REDCHAIN_FIXTURE_DIR")
        if env_dir:
            return Path(env_dir)
        # Bundled minimal fixtures live next to the package.
        return Path(__file__).resolve().parent.parent / "_fixtures"
