"""Interactive REPL and slash commands."""
import time

from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .agent import agent
from .db import cfg_get, cfg_set, list_sessions, load_messages, new_session, push, session_exists
from .onboarding import ask_command_permission, ask_show_agent_loop, setup
from .providers import make_client
from .ui import console


def show_sessions():
    t = Table(title="Recent sessions")
    for col in ("id", "title", "messages", "created"):
        t.add_column(col)
    for i, title, n, ts in list_sessions():
        t.add_row(str(i), title, str(n), time.strftime("%Y-%m-%d %H:%M", time.localtime(ts)))
    console.print(t)


def main():
    c = cfg_get()
    if not c.get("model"):
        c = setup()
    else:
        if "show_agent_loop" not in c:
            cfg_set(show_agent_loop=ask_show_agent_loop())
        if "command_permission" not in c:
            cfg_set(command_permission=ask_command_permission())
        c = cfg_get()
    client = make_client(c)
    sid, history = None, []  # a session row is created on the first message
    console.print(Panel(f"[bold]micro-code: [/]  {c['base_url']}  {c['model']}\n\n"
    "commands:  "
    "/new  - new session\n"
    "/sessions  - show sessions\n"
    "/resume <id>  - resume session\n"
    "/config  - change config\n"
    "/loop  - show agent loop\n"
    "/model - change the model\n"
    "/permission - change the permission\n"
    "/exit  - exit\n",
border_style="blue"))
    while True:
        try:
            q = Prompt.ask("\n[bold blue]>[/]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q in ("/exit", "exit", "quit","exit()"):
            break
        if q == "/new":
            sid, history = None, []
            console.print("[dim]New session.[/]")
        elif q == "/sessions":
            show_sessions()
        elif q.startswith("/resume"):
            arg = q.split()[-1] if " " in q else ""
            if arg.isdigit() and session_exists(int(arg)):
                sid, history = int(arg), load_messages(int(arg))
                console.print(f"[dim]Resumed session {sid} ({len(history)} messages).[/]")
            else:
                console.print("[red]Usage: /resume <id>  (see /sessions)[/]")
        elif q == "/config":
            c = setup()
            client = make_client(c)

        elif q == "/loop":
            cfg_set(show_agent_loop=ask_show_agent_loop(c.get("show_agent_loop")))
            c = cfg_get()
        elif q == "/permission":
            cfg_set(command_permission=ask_command_permission(c.get("command_permission")))
            c = cfg_get()
            console.print(f"[dim]Command permission: {c.get('command_permission', 'ask')}[/]")
        elif q == "/model":
            model = Prompt.ask("Model name")
            cfg_set(model=model)
            c = cfg_get()
            client = make_client(c)
        elif q:
            if sid is None:
                sid = new_session(q[:50])
            push(sid, history, {"role": "user", "content": [{"type": "text", "text": q}]})
            try:
                agent(c, client, sid, history)
            except Exception as e:
                console.print(f"[red]API error:[/] {e}")
