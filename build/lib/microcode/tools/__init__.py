from __future__ import annotations

import json

from ..core import Registry, ToolResult, Workspace
from .filesystem import make_filesystem_tools
from .git import make_git_tools
from .shell import make_shell_tools

__all__ = [
    "TOOLS",
    "build_registry",
    "make_filesystem_tools",
    "make_git_tools",
    "make_shell_tools",
    "registry",
    "run_tool",
    "workspace",
]


def build_registry(ws: Workspace | None = None) -> Registry:
    ws = ws or Workspace()
    registry = Registry()
    for spec in (
        *make_filesystem_tools(ws),
        *make_git_tools(ws),
        *make_shell_tools(ws),
    ):
        registry.register(spec)
    return registry


workspace = Workspace()
registry = build_registry(workspace)
TOOLS = registry.specs()


def run_tool(name: str, arguments: dict | None = None) -> str:
    try:
        result = registry.call(name, arguments)
    except KeyError as exc:
        result = ToolResult(False, "", str(exc))
    return json.dumps(result.to_dict(), ensure_ascii=False)
