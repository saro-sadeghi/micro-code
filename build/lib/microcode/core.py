from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import json
import traceback

from .config import ToolConfig


@dataclass(slots=True)
class ToolResult:
    ok: bool
    output: str
    error: str | None = None
    meta: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {"ok": self.ok, "output": self.output}
        if self.error:
            data["error"] = self.error
        if self.meta:
            data["meta"] = self.meta
        return data


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., ToolResult]

    def schema(self) -> dict[str, Any]:
        required = [
            name for name, spec in self.parameters.items()
            if "default" not in spec and not (
                isinstance(spec.get("type"), list) and "null" in spec["type"]
            )
        ]
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": self.parameters,
            "additionalProperties": False,
        }
        if required:
            input_schema["required"] = required
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": input_schema,
        }


class Workspace:
    def __init__(self, config: ToolConfig | None = None):
        self.config = config or ToolConfig.from_env()
        self.root = self.config.root.resolve()

    def path(self, raw: str) -> Path:
        p = Path(raw)
        candidate = (self.root / p if not p.is_absolute() else p).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError(f"Path escapes workspace: {raw}") from exc
        return candidate

    def rel(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def is_ignored(self, path: Path) -> bool:
        try:
            rel = path.resolve().relative_to(self.root)
        except ValueError:
            return True
        return any(part in self.config.ignores for part in rel.parts)


class Registry:
    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Duplicate tool: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def specs(self) -> list[dict[str, Any]]:
        return [self._tools[k].schema() for k in sorted(self._tools)]

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        spec = self.get(name)
        cleaned = {k: v for k, v in (arguments or {}).items() if v is not None}
        try:
            return spec.handler(**cleaned)
        except Exception as exc:  # defensive boundary for model tool loops
            return ToolResult(
                ok=False,
                output="",
                error=f"{type(exc).__name__}: {exc}",
                meta={"traceback": traceback.format_exc(limit=3)},
            )

    def to_json(self) -> str:
        return json.dumps(self.specs(), indent=2, ensure_ascii=False)
