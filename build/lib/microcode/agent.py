"""The agent loop: call the model, run tools, repeat until no more tool calls."""
import json

from .db import push
from .llm import chat
from .tools import run_tool
from .ui import (
    COMMAND_TOOLS,
    ask_to_run_command,
    command_permission_mode,
    console,
    loop_verbose,
    show_assistant,
    show_loop,
    show_task_done,
    show_task_start,
    show_tool_call,
    show_tool_result,
)


def _denied(name: str) -> str:
    return json.dumps({
        "ok": False,
        "output": "",
        "error": f"User denied {name}",
    }, ensure_ascii=False)


def agent(c, client, sid, history):
    verbose = loop_verbose(c)
    turn = 0
    tool_calls = 0
    if verbose:
        show_task_start()
    while True:
        turn += 1
        if verbose:
            show_loop(turn)
        with console.status("[bold]Thinking...[/]"):
            blocks = chat(c, client, history)
        push(sid, history, {"role": "assistant", "content": blocks})
        results = []
        for b in blocks:
            if b["type"] == "text":
                show_assistant(b["text"])
            elif b["type"] == "tool_use":
                name, args, tool_id = b["name"], b.get("input") or {}, b.get("id", "")
                if verbose:
                    show_tool_call(name, args, tool_id)
                if name in COMMAND_TOOLS and command_permission_mode(c) == "ask":
                    if not ask_to_run_command(name, args):
                        content = _denied(name)
                        if verbose:
                            show_tool_result(name, content)
                        results.append({"type": "tool_result", "tool_use_id": tool_id, "content": content})
                        tool_calls += 1
                        continue
                with console.status(f"[bold yellow]Running {name}...[/]"):
                    content = run_tool(name, args)
                if verbose:
                    show_tool_result(name, content)
                results.append({"type": "tool_result", "tool_use_id": tool_id, "content": content})
                tool_calls += 1
        if not results:
            if verbose:
                show_task_done(turn, tool_calls)
            return
        push(sid, history, {"role": "user", "content": results})
