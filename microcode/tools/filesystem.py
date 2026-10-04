from __future__ import annotations

from pathlib import Path
import fnmatch
import os
import re
import shutil

from ..core import ToolResult, ToolSpec, Workspace


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    kept = max(0, limit - 160)
    return text[:kept] + f"\n… [truncated, {len(text) - kept} chars omitted]"


def _text(path: Path, max_bytes: int) -> tuple[str, bool]:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
        truncated = True
    else:
        truncated = False
    if b"\x00" in raw[:4096]:
        raise ValueError("Binary file is not supported")
    return raw.decode("utf-8", errors="replace"), truncated


def make_filesystem_tools(ws: Workspace) -> list[ToolSpec]:
    cfg = ws.config

    def list_dir(path: str = ".", recursive: bool = False, max_entries: int = 200) -> ToolResult:
        base = ws.path(path)
        if not base.exists():
            return ToolResult(False, "", f"Not found: {path}")
        if not base.is_dir():
            return ToolResult(False, "", f"Not a directory: {path}")

        rows: list[str] = []
        if recursive:
            for item in base.rglob("*"):
                if ws.is_ignored(item):
                    continue
                rows.append(f"{ws.rel(item)}{'/' if item.is_dir() else ''}")
                if len(rows) >= max_entries:
                    break
        else:
            for item in sorted(base.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if ws.is_ignored(item):
                    continue
                rows.append(f"{item.name}{'/' if item.is_dir() else ''}")
                if len(rows) >= max_entries:
                    break
        return ToolResult(True, "\n".join(rows) or "(empty)", meta={"count": len(rows)})

    def read_file(path: str, start_line: int | None = None, end_line: int | None = None) -> ToolResult:
        p = ws.path(path)
        if not p.exists():
            return ToolResult(False, "", f"Not found: {path}")
        if not p.is_file():
            return ToolResult(False, "", f"Not a file: {path}")
        try:
            text, truncated_bytes = _text(p, cfg.max_file_bytes)
        except (OSError, ValueError) as exc:
            return ToolResult(False, "", str(exc))
        lines = text.splitlines()
        start = max(1, start_line or 1)
        end = min(len(lines), end_line or len(lines))
        if start > end and lines:
            return ToolResult(False, "", f"Invalid line range: {start}-{end}")
        numbered = "\n".join(f"{i:>5} | {lines[i-1]}" for i in range(start, end + 1))
        numbered = _clip(numbered, cfg.max_read_chars)
        return ToolResult(True, numbered or "(empty file)", meta={"lines": len(lines), "byte_truncated": truncated_bytes})

    def write_file(path: str, content: str) -> ToolResult:
        p = ws.path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8")
        if len(data) > cfg.max_file_bytes:
            return ToolResult(False, "", f"Content too large: {len(data)} bytes")
        try:
            p.write_bytes(data)
        except OSError as exc:
            return ToolResult(False, "", str(exc))
        return ToolResult(True, f"Wrote {ws.rel(p)} ({len(data)} bytes)")

    def edit_file(path: str, old: str, new: str, replace_all: bool = False) -> ToolResult:
        p = ws.path(path)
        if not p.exists() or not p.is_file():
            return ToolResult(False, "", f"File not found: {path}")
        try:
            original, _ = _text(p, cfg.max_file_bytes)
        except (OSError, ValueError) as exc:
            return ToolResult(False, "", str(exc))
        count = original.count(old)
        if count == 0:
            return ToolResult(False, "", "Old text was not found")
        if count > 1 and not replace_all:
            return ToolResult(False, "", f"Old text matches {count} locations; set replace_all=true")
        updated = original.replace(old, new, -1 if replace_all else 1)
        p.write_text(updated, encoding="utf-8")
        return ToolResult(True, f"Edited {ws.rel(p)}; replacements={count if replace_all else 1}")

    def apply_patch(path: str, patch: str, max_hunks: int = 50) -> ToolResult:
        """Apply a compact unified diff to a single file using only stdlib parsing."""
        p = ws.path(path)
        if not p.is_file():
            return ToolResult(False, "", f"File not found: {path}")
        original = p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        lines = patch.splitlines(keepends=True)
        if not lines:
            return ToolResult(False, "", "Empty patch")
        hunks = []
        i = 0
        while i < len(lines):
            m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[i])
            if not m:
                i += 1
                continue
            if len(hunks) >= max_hunks:
                return ToolResult(False, "", f"Patch exceeds max_hunks={max_hunks}")
            old_start, old_count, new_start, new_count = [int(x or 1) for x in m.groups()]
            i += 1
            body = []
            while i < len(lines) and not lines[i].startswith("@@ "):
                if lines[i].startswith(("+", "-", " ")):
                    body.append(lines[i])
                i += 1
            hunks.append((old_start, old_count, new_start, new_count, body))

        if not hunks:
            return ToolResult(False, "", "No unified-diff hunks found")

        out: list[str] = []
        cursor = 1
        for old_start, old_count, _new_start, _new_count, body in hunks:
            if old_start < cursor or old_start > len(original) + 1:
                return ToolResult(False, "", f"Invalid hunk location: {old_start}")
            out.extend(original[cursor - 1 : old_start - 1])
            idx = old_start - 1
            consumed = 0
            for row in body:
                tag = row[:1]
                content = row[1:]
                if tag == " ":
                    if idx >= len(original) or original[idx] != content:
                        return ToolResult(False, "", f"Context mismatch at original line {idx + 1}")
                    out.append(original[idx])
                    idx += 1
                    consumed += 1
                elif tag == "-":
                    if idx >= len(original) or original[idx] != content:
                        return ToolResult(False, "", f"Delete mismatch at original line {idx + 1}")
                    idx += 1
                    consumed += 1
                elif tag == "+":
                    out.append(content)
                else:
                    return ToolResult(False, "", f"Unsupported patch row: {row!r}")
            if consumed != old_count:
                return ToolResult(False, "", f"Hunk expected {old_count} old lines, consumed {consumed}")
            cursor = idx + 1
        out.extend(original[cursor - 1 :])
        p.write_text("".join(out), encoding="utf-8")
        return ToolResult(True, f"Applied patch to {ws.rel(p)} ({len(hunks)} hunks)")

    def find_files(pattern: str = "**/*", path: str = ".", max_results: int = 200) -> ToolResult:
        base = ws.path(path)
        if not base.is_dir():
            return ToolResult(False, "", f"Not a directory: {path}")
        rows: list[str] = []
        for p in base.rglob("*"):
            if ws.is_ignored(p) or not p.is_file():
                continue
            rel = p.relative_to(base).as_posix()
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(p.name, pattern):
                rows.append(ws.rel(p))
                if len(rows) >= max_results:
                    break
        return ToolResult(True, "\n".join(rows) or "(no matches)", meta={"count": len(rows)})

    def search_text(query: str, path: str = ".", regex: bool = False, case_sensitive: bool = False,
                    max_results: int = 100, context_lines: int = 1) -> ToolResult:
        base = ws.path(path)
        if not base.exists():
            return ToolResult(False, "", f"Not found: {path}")
        pattern = re.compile(query if regex else re.escape(query), 0 if case_sensitive else re.IGNORECASE)
        hits: list[str] = []
        files = [base] if base.is_file() else (p for p in base.rglob("*") if p.is_file())
        for p in files:
            if ws.is_ignored(p):
                continue
            try:
                text, _ = _text(p, cfg.max_file_bytes)
            except (OSError, ValueError):
                continue
            rows = text.splitlines()
            for i, line in enumerate(rows):
                if pattern.search(line):
                    lo = max(0, i - context_lines)
                    hi = min(len(rows), i + context_lines + 1)
                    chunk = "\n".join(f"{j+1:>5} | {rows[j]}" for j in range(lo, hi))
                    hits.append(f"{ws.rel(p)}\n{chunk}")
                    if len(hits) >= max_results:
                        return ToolResult(True, "\n---\n".join(hits), meta={"count": len(hits), "truncated": True})
        return ToolResult(True, "\n---\n".join(hits) or "(no matches)", meta={"count": len(hits), "truncated": False})

    def move_path(src: str, dst: str) -> ToolResult:
        s, d = ws.path(src), ws.path(dst)
        if not s.exists():
            return ToolResult(False, "", f"Source not found: {src}")
        if d.exists():
            return ToolResult(False, "", f"Destination already exists: {dst}")
        d.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(s), str(d))
        except OSError as exc:
            return ToolResult(False, "", str(exc))
        return ToolResult(True, f"Moved {src} -> {dst}")

    def delete_path(path: str, recursive: bool = False) -> ToolResult:
        if not cfg.allow_delete:
            return ToolResult(False, "", "Delete is disabled by configuration")
        p = ws.path(path)
        if not p.exists():
            return ToolResult(False, "", f"Not found: {path}")
        if p.is_dir():
            if not recursive:
                return ToolResult(False, "", "Directory delete requires recursive=true")
            shutil.rmtree(p)
        else:
            p.unlink()
        return ToolResult(True, f"Deleted {path}")

    def file_info(path: str) -> ToolResult:
        p = ws.path(path)
        if not p.exists():
            return ToolResult(False, "", f"Not found: {path}")
        stat = p.stat()
        return ToolResult(True, f"{ws.rel(p)}\ntype={'dir' if p.is_dir() else 'file'}\nsize={stat.st_size}\nmodified={stat.st_mtime}")

    return [
        ToolSpec("list_dir", "List files/directories in the workspace.", {
            "path": {"type": "string", "default": "."},
            "recursive": {"type": "boolean", "default": False},
            "max_entries": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 200},
        }, list_dir),
        ToolSpec("read_file", "Read a text file, optionally by 1-based line range.", {
            "path": {"type": "string"},
            "start_line": {"type": ["integer", "null"]},
            "end_line": {"type": ["integer", "null"]},
        }, read_file),
        ToolSpec("write_file", "Create or overwrite a UTF-8 text file.", {
            "path": {"type": "string"}, "content": {"type": "string"},
        }, write_file),
        ToolSpec("edit_file", "Replace an exact text fragment in a file.", {
            "path": {"type": "string"}, "old": {"type": "string"},
            "new": {"type": "string"}, "replace_all": {"type": "boolean", "default": False},
        }, edit_file),
        ToolSpec("apply_patch", "Apply a unified diff to one file.", {
            "path": {"type": "string"}, "patch": {"type": "string"},
        }, apply_patch),
        ToolSpec("find_files", "Find files by a glob pattern without scanning ignored directories.", {
            "pattern": {"type": "string", "default": "**/*"},
            "path": {"type": "string", "default": "."},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 200},
        }, find_files),
        ToolSpec("search_text", "Search text across files with optional regex and context lines.", {
            "query": {"type": "string"}, "path": {"type": "string", "default": "."},
            "regex": {"type": "boolean", "default": False}, "case_sensitive": {"type": "boolean", "default": False},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 500, "default": 100},
            "context_lines": {"type": "integer", "minimum": 0, "maximum": 5, "default": 1},
        }, search_text),
        ToolSpec("move_path", "Move a file or directory inside the workspace.", {
            "src": {"type": "string"}, "dst": {"type": "string"},
        }, move_path),
        ToolSpec("delete_path", "Delete a file or directory inside the workspace.", {
            "path": {"type": "string"}, "recursive": {"type": "boolean", "default": False},
        }, delete_path),
        ToolSpec("file_info", "Return basic metadata for a path.", {"path": {"type": "string"}}, file_info),
    ]
