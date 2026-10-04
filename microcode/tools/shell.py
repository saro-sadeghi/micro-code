from __future__ import annotations

import os
import shlex
import subprocess

from ..core import ToolResult, ToolSpec, Workspace


DANGEROUS_PREFIXES = (
    "rm -rf /", "rm -rf ~", "mkfs", "format c:", "shutdown", "reboot",
)


def make_shell_tools(ws: Workspace) -> list[ToolSpec]:
    def run_command(command: str, timeout: float | None = None, max_output_chars: int | None = None,
                    env: dict[str, str] | None = None) -> ToolResult:
        cmd_lower = command.strip().lower()
        if any(cmd_lower.startswith(prefix) for prefix in DANGEROUS_PREFIXES):
            return ToolResult(False, "", "Command blocked by Micro Code safety filter")
        timeout_value = timeout if timeout is not None else ws.config.command_timeout
        output_limit = max_output_chars if max_output_chars is not None else ws.config.max_output_chars
        merged_env = os.environ.copy()
        if env:
            merged_env.update({str(k): str(v) for k, v in env.items()})
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(ws.root),
                env=merged_env,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout_value,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout or "")
            stderr = (exc.stderr or "")
            return ToolResult(False, (stdout + stderr)[:output_limit], f"Command timed out after {timeout_value}s")
        except OSError as exc:
            return ToolResult(False, "", str(exc))
        combined = ""
        if proc.stdout:
            combined += proc.stdout
        if proc.stderr:
            combined += ("\n" if combined else "") + proc.stderr
        if len(combined) > output_limit:
            combined = combined[: output_limit - 120] + "\n… [output truncated]"
        return ToolResult(proc.returncode == 0, combined or f"(exit code {proc.returncode})", meta={"exit_code": proc.returncode})

    def run_script(command: str, args: list[str] | None = None, timeout: float | None = None) -> ToolResult:
        parts = [command] + [str(a) for a in (args or [])]
        return run_command(" ".join(shlex.quote(x) for x in parts), timeout=timeout)

    return [
        ToolSpec("run_command", "Run a shell command from the workspace root. Output is capped.", {
            "command": {"type": "string"},
            "timeout": {"type": ["number", "null"]},
            "max_output_chars": {"type": ["integer", "null"]},
            "env": {"type": ["object", "null"], "additionalProperties": {"type": "string"}},
        }, run_command),
        ToolSpec("run_script", "Run a command with separately supplied argv values.", {
            "command": {"type": "string"},
            "args": {"type": ["array", "null"], "items": {"type": "string"}},
            "timeout": {"type": ["number", "null"]},
        }, run_script),
    ]
