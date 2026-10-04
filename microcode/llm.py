"""LLM calls. Messages are stored Anthropic-style and converted for OpenAI-compatible APIs."""
import json

from .tools import TOOLS, workspace

SYSTEM = (
    f"You are a coding agent. Working dir: {workspace.root}. "
    "Use tools to inspect, edit, run, and verify work. Be concise."
)


def to_openai(messages):
    """Convert stored Anthropic-style messages to OpenAI chat format."""
    out = [{"role": "system", "content": SYSTEM}]
    for m in messages:
        if m["role"] == "user":
            for b in m["content"]:
                if b["type"] == "tool_result":
                    out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": b["content"]})
                else:
                    out.append({"role": "user", "content": b["text"]})
        else:
            text = "".join(b["text"] for b in m["content"] if b["type"] == "text")
            calls = [{"id": b["id"], "type": "function",
                      "function": {"name": b["name"], "arguments": json.dumps(b["input"])}}
                     for b in m["content"] if b["type"] == "tool_use"]
            msg = {"role": "assistant", "content": text or None}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
    return out


def chat(c, client, history):
    """Return a list of blocks: {"type":"text",...} or {"type":"tool_use",...}."""
    blocks = []
    if c["provider"] == "anthropic":
        r = client.messages.create(model=c["model"], max_tokens=4096, system=SYSTEM,
                                   tools=TOOLS, messages=history)
        for b in r.content:
            if b.type == "text":
                blocks.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                blocks.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
    else:
        tools = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                   "parameters": t["input_schema"]}} for t in TOOLS]
        m = client.chat.completions.create(model=c["model"], messages=to_openai(history),
                                           tools=tools).choices[0].message
        if m.content:
            blocks.append({"type": "text", "text": m.content})
        for tc in m.tool_calls or []:
            blocks.append({"type": "tool_use", "id": tc.id, "name": tc.function.name,
                           "input": json.loads(tc.function.arguments or "{}")})
    return blocks or [{"type": "text", "text": "(no response)"}]
