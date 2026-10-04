from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os


DEFAULT_IGNORES = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "target", "vendor", "bin", "obj",
}


@dataclass(slots=True)
class ToolConfig:
    root: Path = field(default_factory=lambda: Path.cwd().resolve())
    max_output_chars: int = 12000
    max_read_chars: int = 20000
    max_search_results: int = 100
    command_timeout: float = 30.0
    max_file_bytes: int = 2_000_000
    ignores: set[str] = field(default_factory=lambda: set(DEFAULT_IGNORES))
    allow_delete: bool = True

    @classmethod
    def from_env(cls, root: Path | None = None) -> "ToolConfig":
        cfg = cls(root=Path(root or Path.cwd()).resolve())
        if value := os.getenv("MICRO_MAX_OUTPUT_CHARS"):
            cfg.max_output_chars = int(value)
        if value := os.getenv("MICRO_MAX_READ_CHARS"):
            cfg.max_read_chars = int(value)
        if value := os.getenv("MICRO_COMMAND_TIMEOUT"):
            cfg.command_timeout = float(value)
        if value := os.getenv("MICRO_ALLOW_DELETE"):
            cfg.allow_delete = value.lower() in {"1", "true", "yes", "on"}
        return cfg
