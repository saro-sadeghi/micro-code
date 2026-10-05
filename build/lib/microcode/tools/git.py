from __future__ import annotations

import subprocess

from ..core import ToolResult, ToolSpec, Workspace


def make_git_tools(ws: Workspace) -> list[ToolSpec]:
    def git(args: list[str], max_chars: int | None = None) -> ToolResult:
        limit = max_chars or ws.config.max_output_chars
        try:
            proc = subprocess.run(
                ["git", *args], cwd=str(ws.root), capture_output=True,
                text=True, errors="replace", timeout=ws.config.command_timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return ToolResult(False, "", f"git failed: {exc}")
        out = (proc.stdout + ("\n" + proc.stderr if proc.stderr else "")).strip()
        if len(out) > limit:
            out = out[:limit - 100] + "\n… [output truncated]"
        return ToolResult(proc.returncode == 0, out or "(no output)", meta={"exit_code": proc.returncode})

    def git_status() -> ToolResult:
        return git(["status", "--short", "--branch"])

    def git_diff(staged: bool = False, path: str | None = None) -> ToolResult:
        args = ["diff", "--no-ext-diff", "--unified=3"]
        if staged:
            args.insert(1, "--cached")
        if path:
            args += ["--", ws.rel(ws.path(path))]
        return git(args)

    def git_log(count: int = 10, oneline: bool = True) -> ToolResult:
        args = ["log", f"-n{max(1, min(count, 100))}"]
        if oneline:
            args.append("--oneline")
        return git(args)

    def git_show(revision: str = "HEAD", path: str | None = None) -> ToolResult:
        args = ["show", revision]
        if path:
            args += ["--", ws.rel(ws.path(path))]
        return git(args)

    return [
        ToolSpec("git_status", "Show concise git branch and working tree status.", {}, git_status),
        ToolSpec("git_diff", "Show unstaged or staged git diff.", {
            "staged": {"type": "boolean", "default": False},
            "path": {"type": ["string", "null"]},
        }, git_diff),
        ToolSpec("git_log", "Show recent git commits.", {
            "count": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
            "oneline": {"type": "boolean", "default": True},
        }, git_log),
        ToolSpec("git_show", "Show a git revision, optionally for one path.", {
            "revision": {"type": "string", "default": "HEAD"},
            "path": {"type": ["string", "null"]},
        }, git_show),
    ]
