"""Artifact persistence — render Jinja2 templates and write to ``artifacts/``."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


class ArtifactStore:
    def __init__(self, engagement_dir: Path):
        self.engagement_dir = engagement_dir
        self.artifacts_dir = engagement_dir / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._env = self._build_env()

    @staticmethod
    def _build_env() -> Environment:
        templates_path = resources.files("redchain.templates")
        return Environment(
            loader=FileSystemLoader(str(templates_path)),
            autoescape=select_autoescape([]),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, context: dict) -> str:
        template = self._env.get_template(template_name)
        return template.render(**context)

    def write(self, filename: str, content: str) -> Path:
        path = self.artifacts_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def render_and_write(self, template_name: str, filename: str, context: dict) -> Path:
        return self.write(filename, self.render(template_name, context))

    def read(self, filename: str) -> str | None:
        path = self.artifacts_dir / filename
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def path(self, filename: str) -> Path:
        return self.artifacts_dir / filename
