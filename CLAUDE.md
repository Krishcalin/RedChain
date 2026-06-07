# CLAUDE.md — RedChain

## Project Overview

RedChain is a Python red-team engagement orchestrator. It runs offensive security engagements as a **gated state machine** — one phase, one specialist agent, one validated artifact at a time. Built on the Anthropic SDK with prompt caching, designed for multi-day engagements with checkpoint/resume.

This is a **runtime application**, not a Claude Code configuration. Specialist agents are Python classes that call the Anthropic API; the orchestrator owns control flow.

**Repository**: https://github.com/Krishcalin/RedChain
**License**: MIT
**Language**: Python 3.10+

## Architecture

```
src/redchain/
├── runtime/        Orchestrator, state store, artifact store, agent session wrapper
├── phases/         One module per Kill Chain phase
├── agents/         Specialist agent classes
├── gates/          Artifact validators
├── skills/         Reusable Python modules
├── integrations/   Tool wrappers (subprocess + JSON parsing)
├── templates/      Jinja2 templates for artifacts
├── presets/        YAML engagement templates
└── vulnref/        Vulnerability pattern library
```

### Control flow (one engagement)

1. `cli.engage` → loads preset, creates engagement dir, initializes `state.sqlite` and `manifest.yaml`.
2. `Orchestrator.run()` iterates through `preset.phases` in order.
3. For each phase:
   - `Phase.entry_contract()` — verifies prerequisite artifacts exist.
   - `Phase.execute()` — dispatches one or more `Agent` calls, possibly invoking `Skill`s and `Integration`s.
   - `Phase.write_artifact()` — renders Jinja2 template, persists to `artifacts/`.
   - `Gate.validate()` — checks artifact completeness. On failure, phase stays `failed_gate` and orchestrator pauses (resumable).
4. State is persisted between phases; `redchain resume` picks up at the next unsatisfied phase.

## Conventions

- **Phases own orchestration logic**, agents own LLM calls, skills own reusable Python helpers, integrations own subprocess.
- Every agent run produces a transcript JSONL in `transcripts/`. Never store secrets in transcripts.
- Artifacts are markdown files rendered from Jinja2 templates with a structured pydantic model. The model is the source of truth, the markdown is the human view.
- Gates are pydantic-validation-driven where possible; for richer checks, gates may call an `Agent` (a reviewer) — but a gate must never modify artifacts.
- Use `--dry-run` mode for CI: agents return canned responses from `tests/fixtures/`. Production code must check `runtime.is_dry_run()` before any API call.

## Adding things

### New phase

1. `src/redchain/phases/<name>.py` — subclass `Phase`, implement `execute()`.
2. `src/redchain/gates/<name>_gate.py` — subclass `Gate`, implement `validate()`.
3. `src/redchain/templates/<name>_artifact.md.j2` — Jinja2 template.
4. Register in `phases/__init__.py:PHASE_REGISTRY`.
5. Reference in a preset under `phases:`.
6. Add a test in `tests/test_phase_<name>.py`.

### New agent

1. `src/redchain/agents/<name>.py` — subclass `Agent`, set `SYSTEM_PROMPT`, override `tools` if needed.
2. Register in `agents/__init__.py:AGENT_REGISTRY`.
3. Add a test that runs in `--dry-run` mode with a fixture.

### New integration

1. `src/redchain/integrations/<name>.py` — subclass `Integration`, implement `run()` returning a parsed pydantic model.
2. The subprocess invocation must accept a `timeout` and never inject unsanitized strings.

## Testing

- `pytest` — unit tests, no API key required, run in `--dry-run` mode for agent code.
- `pytest -m live` — live API tests, opt-in only.
- `tests/fixtures/` — canned agent responses for dry-run mode.

## Out of scope for v0.1.0

- Phases beyond `scope` / `recon` / `report` (stubs only).
- Real exploit execution — RedChain plans and validates, it does not weaponize live targets in MVP.
- Multi-user / SaaS deployment — engagement state is local SQLite.

## Security and ethics

RedChain is for **authorized engagements only**. The orchestrator does not gate this — the operator is responsible for ensuring scope and authorization. Never run against targets you do not own or have written permission to test.
