"""First-run setup: choose provider, model and API key."""
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .db import cfg_get, cfg_set
from .providers import PROVIDERS
from .ui import console, is_truthy


def pick(title, options, allow_other=True):
    """Numbered menu. Returns the chosen option, or None if 'Other' was chosen."""
    for i, o in enumerate(options, 1):
        console.print(f"  [cyan]{i}[/]. {o}")
    n = len(options) + 1
    if allow_other:
        console.print(f"  [cyan]{n}[/]. Other (type your own)")
    top = n if allow_other else n - 1
    c = int(Prompt.ask(title, choices=[str(i) for i in range(1, top + 1)], default="1"))
    return options[c - 1] if c < n else None


def setup():
    console.print(Panel("[bold]Setup[/]  choose provider, model and API key", border_style="blue"))
    keys = list(PROVIDERS)
    labels = [PROVIDERS[k]["label"] for k in keys]
    provider = keys[labels.index(pick("Provider", labels, allow_other=False))]
    base_url = PROVIDERS[provider]["base_url"]
    if provider == "custom":
        base_url = Prompt.ask("Base URL", default="http://localhost:11434/v1")
    presets = PROVIDERS[provider]["models"]
    model = pick("Model", presets) if presets else None
    model = model or Prompt.ask("Model name")
    api_key = Prompt.ask("API key (empty = none)", password=True) or "none"
    show_agent_loop = ask_show_agent_loop(cfg_get().get("show_agent_loop"))
    cfg_set(provider=provider, model=model, api_key=api_key, base_url=base_url,
            show_agent_loop=show_agent_loop)
    console.print("[green]Saved.[/]")
    return cfg_get()


def ask_show_agent_loop(current=None):
    """Ask whether to print agent loops and tool calls. Default is off."""
    enabled = Confirm.ask(
        "Show agent loop and tool calls in the terminal?",
        default=is_truthy(current),
    )
    return "1" if enabled else "0"
