"""SQLite-backed engagement state.

One SQLite file per engagement, stored at ``<engagement_dir>/state.sqlite``.
Tracks per-phase status, gate decisions, and a pointer index into transcripts
written on disk under ``<engagement_dir>/transcripts/``.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class PhaseStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_GATE = "awaiting_gate"
    FAILED_GATE = "failed_gate"
    COMPLETED = "completed"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS engagement (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS phases (
    name TEXT PRIMARY KEY,
    position INTEGER NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    artifact_path TEXT,
    gate_reason TEXT
);

CREATE TABLE IF NOT EXISTS gate_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    passed INTEGER NOT NULL,
    reason TEXT,
    artifact_path TEXT,
    FOREIGN KEY (phase) REFERENCES phases(name)
);

CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase TEXT NOT NULL,
    agent TEXT NOT NULL,
    started_at TEXT NOT NULL,
    transcript_path TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    cache_creation_tokens INTEGER
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class PhaseRecord:
    name: str
    position: int
    status: PhaseStatus
    started_at: str | None
    completed_at: str | None
    artifact_path: str | None
    gate_reason: str | None


class EngagementState:
    """Persistent, resumable engagement state backed by SQLite."""

    def __init__(self, engagement_dir: Path):
        self.engagement_dir = engagement_dir
        self.db_path = engagement_dir / "state.sqlite"
        engagement_dir.mkdir(parents=True, exist_ok=True)
        (engagement_dir / "artifacts").mkdir(exist_ok=True)
        (engagement_dir / "transcripts").mkdir(exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "EngagementState":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def initialize(self, *, target: str, preset: str, phases: list[str]) -> None:
        """Idempotent — safe to call on resume."""
        cur = self._conn.cursor()
        meta = {
            "target": target,
            "preset": preset,
            "created_at": _now(),
        }
        for key, value in meta.items():
            cur.execute(
                "INSERT INTO engagement(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO NOTHING",
                (key, value),
            )
        for position, name in enumerate(phases):
            cur.execute(
                "INSERT INTO phases(name, position, status) VALUES(?, ?, ?) "
                "ON CONFLICT(name) DO NOTHING",
                (name, position, PhaseStatus.PENDING.value),
            )
        self._conn.commit()

    def metadata(self) -> dict[str, str]:
        cur = self._conn.execute("SELECT key, value FROM engagement")
        return dict(cur.fetchall())

    def phase(self, name: str) -> PhaseRecord | None:
        row = self._conn.execute(
            "SELECT name, position, status, started_at, completed_at, "
            "artifact_path, gate_reason FROM phases WHERE name = ?",
            (name,),
        ).fetchone()
        if not row:
            return None
        return PhaseRecord(
            name=row[0],
            position=row[1],
            status=PhaseStatus(row[2]),
            started_at=row[3],
            completed_at=row[4],
            artifact_path=row[5],
            gate_reason=row[6],
        )

    def phases(self) -> list[PhaseRecord]:
        rows = self._conn.execute(
            "SELECT name, position, status, started_at, completed_at, "
            "artifact_path, gate_reason FROM phases ORDER BY position"
        ).fetchall()
        return [
            PhaseRecord(
                name=r[0],
                position=r[1],
                status=PhaseStatus(r[2]),
                started_at=r[3],
                completed_at=r[4],
                artifact_path=r[5],
                gate_reason=r[6],
            )
            for r in rows
        ]

    def next_pending_phase(self) -> PhaseRecord | None:
        for record in self.phases():
            if record.status in (PhaseStatus.PENDING, PhaseStatus.FAILED_GATE):
                return record
        return None

    def mark_running(self, phase: str) -> None:
        self._conn.execute(
            "UPDATE phases SET status = ?, started_at = COALESCE(started_at, ?) "
            "WHERE name = ?",
            (PhaseStatus.RUNNING.value, _now(), phase),
        )
        self._conn.commit()

    def mark_awaiting_gate(self, phase: str, artifact_path: Path) -> None:
        self._conn.execute(
            "UPDATE phases SET status = ?, artifact_path = ? WHERE name = ?",
            (PhaseStatus.AWAITING_GATE.value, str(artifact_path), phase),
        )
        self._conn.commit()

    def record_gate_decision(
        self,
        phase: str,
        *,
        passed: bool,
        reason: str,
        artifact_path: Path | None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO gate_decisions(phase, decided_at, passed, reason, artifact_path) "
            "VALUES(?, ?, ?, ?, ?)",
            (
                phase,
                _now(),
                1 if passed else 0,
                reason,
                str(artifact_path) if artifact_path else None,
            ),
        )
        if passed:
            self._conn.execute(
                "UPDATE phases SET status = ?, completed_at = ?, gate_reason = NULL "
                "WHERE name = ?",
                (PhaseStatus.COMPLETED.value, _now(), phase),
            )
        else:
            self._conn.execute(
                "UPDATE phases SET status = ?, gate_reason = ? WHERE name = ?",
                (PhaseStatus.FAILED_GATE.value, reason, phase),
            )
        self._conn.commit()

    def record_transcript(
        self,
        *,
        phase: str,
        agent: str,
        transcript_path: Path,
        usage: dict[str, int] | None = None,
    ) -> None:
        u = usage or {}
        self._conn.execute(
            "INSERT INTO transcripts(phase, agent, started_at, transcript_path, "
            "input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (
                phase,
                agent,
                _now(),
                str(transcript_path),
                u.get("input_tokens"),
                u.get("output_tokens"),
                u.get("cache_read_input_tokens"),
                u.get("cache_creation_input_tokens"),
            ),
        )
        self._conn.commit()

    def transcripts(self, phase: str | None = None) -> list[dict]:
        sql = (
            "SELECT phase, agent, started_at, transcript_path, "
            "input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens "
            "FROM transcripts"
        )
        params: tuple = ()
        if phase:
            sql += " WHERE phase = ?"
            params = (phase,)
        sql += " ORDER BY id"
        rows = self._conn.execute(sql, params).fetchall()
        return [
            {
                "phase": r[0],
                "agent": r[1],
                "started_at": r[2],
                "transcript_path": r[3],
                "input_tokens": r[4],
                "output_tokens": r[5],
                "cache_read_tokens": r[6],
                "cache_creation_tokens": r[7],
            }
            for r in rows
        ]

    def summary(self) -> dict:
        return {
            "metadata": self.metadata(),
            "phases": [
                {
                    "name": p.name,
                    "status": p.status.value,
                    "artifact": p.artifact_path,
                    "gate_reason": p.gate_reason,
                    "started_at": p.started_at,
                    "completed_at": p.completed_at,
                }
                for p in self.phases()
            ],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.summary(), indent=indent)
