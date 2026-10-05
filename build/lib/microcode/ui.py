"""Shared Rich console and agent-loop display."""
from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax

console = Console()

COMMAND_TOOLS = frozenset({"run_command", "run_script"})


def is_truthy(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def loop_verbose(cfg: dict | None) -> bool:
    return is_truthy((cfg or {}).get("show_agent_loop"))


def command_permission_mode(cfg: dict | None) -> str:
    value = str((cfg or {}).get("command_permission") or "ask").strip().lower()
    if value in {"allow", "always", "auto"}:
        return "allow"
    return "ask"


def command_preview(name: str, arguments: dict | None) -> str:
    args = arguments or {}
    if name == "run_command":
        return str(args.get("command") or "")
    if name == "run_script":
        parts = [str(args.get("command") or "")]
        parts.extend(str(a) for a in (args.get("args") or []))
        return " ".join(p for p in parts if p).strip()
    return json.dumps(_clip_args(args), indent=2, ensure_ascii=False)


def ask_to_run_command(name: str, arguments: dict | None) -> bool:
    preview = command_preview(name, arguments) or "(empty)"
    console.print(Panel(
        preview,
        title=f"[bold yellow]permission[/] {name}",
        border_style="yellow",
        expand=False,
    ))
    return Confirm.ask("Run this command?", default=False)

_ARG_STR_LIMIT = 400
_RESULT_LIMIT = 4000


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return text[:limit] + f"\n… [{omitted} chars omitted]"


def _clip_args(value: Any, limit: int = _ARG_STR_LIMIT) -> Any:
    if isinstance(value, dict):
        return {k: _clip_args(v, limit) for k, v in value.items()}
    if isinstance(value, list):
        shown = [_clip_args(item, limit) for item in value[:20]]
        if len(value) > 20:
            shown.append(f"… [{len(value) - 20} more items]")
        return shown
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + f"… [{len(value)} chars]"
    return value


def show_task_start() -> None:
    console.rule("[bold blue]agent[/]")


def show_loop(turn: int) -> None:
    console.rule(f"[bold cyan]loop {turn}[/]")


def show_assistant(text: str) -> None:
    console.print(Markdown(text))


def show_tool_call(name: str, arguments: dict | None, tool_id: str = "") -> None:
    payload = json.dumps(_clip_args(arguments or {}), indent=2, ensure_ascii=False)
    subtitle = f"[dim]{tool_id}[/]" if tool_id else None
    console.print(Panel(
        Syntax(payload, "json", theme="ansi_dark", word_wrap=True),
        title=f"[bold yellow]call[/] {name}",
        subtitle=subtitle,
        border_style="yellow",
        expand=False,
    ))


def show_tool_result(name: str, content: str) -> None:
    try:
        data = json.loads(content)
    except (TypeError, ValueError):
        data = None

    if isinstance(data, dict) and "ok" in data:
        ok = bool(data.get("ok"))
        parts = []
        if data.get("output"):
            parts.append(str(data["output"]))
        if data.get("error"):
            parts.append(f"error: {data['error']}")
        if data.get("meta"):
            parts.append(f"meta: {json.dumps(data['meta'], ensure_ascii=False)}")
        body = "\n".join(parts) or "(empty)"
        style = "green" if ok else "red"
        title = f"[bold {style}]{'ok' if ok else 'fail'}[/] {name}"
    else:
        body = content
        style = "white"
        title = f"[bold]result[/] {name}"

    console.print(Panel(
        _clip(body, _RESULT_LIMIT),
        title=title,
        border_style=style,
        expand=False,
    ))


def show_task_done(turns: int, tool_calls: int) -> None:
    console.print(
        f"[dim]finished in {turns} loop{'s' if turns != 1 else ''}, "
        f"{tool_calls} tool call{'s' if tool_calls != 1 else ''}[/]"
    )
