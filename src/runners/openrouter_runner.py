"""
OpenRouter agent runner — implements the `local` backend in runner_abstract.

Drives buyer/seller/mediator through the same prompt contract as the Claude
Code / OpenCode runners, but via OpenRouter's OpenAI-compatible chat API with
function-calling. Default model is meta-llama/llama-3.3-70b-instruct.

Role-based access control mirrors the PreToolUse hook used by the `claude`
runner: buyer cannot read or write kg-seller/, seller cannot touch kg-buyer/.
The mediator can read both, but the negotiate.py merge step only stages
kg-shared/ + sessions/ for the mediator anyway.

Env:
    OPENROUTER_API_KEY  required
    OPENROUTER_MODEL    optional, default meta-llama/llama-3.3-70b-instruct
    OPENROUTER_MAX_STEPS optional, default 30
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from openai import OpenAI


DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"
DEFAULT_MAX_STEPS = 30

ROLE_FORBIDDEN: dict[str, tuple[str, ...]] = {
    "buyer": ("kg-seller/",),
    "seller": ("kg-buyer/",),
    "mediator": (),
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file relative to the project root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create or overwrite a UTF-8 text file relative to the project "
                "root. Parent directories are created as needed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List entries (files and subdirs) in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": (
                "Call this when you have completed your move for the round. "
                "Must be called before exiting."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _check_access(role: str, path: str) -> str | None:
    """Return an error string if `role` may not touch `path`, else None."""
    if not path:
        return "Empty path is not allowed"
    norm = path.replace("\\", "/")
    if norm.startswith("/"):
        return f"Absolute paths are not allowed: {path!r}"
    if ".." in Path(norm).parts:
        return f"Path traversal is not allowed: {path!r}"
    if norm.startswith("./"):
        norm = norm[2:]
    for forbidden in ROLE_FORBIDDEN.get(role, ()):
        if norm == forbidden.rstrip("/") or norm.startswith(forbidden):
            return f"Access denied: {role!r} may not access {forbidden!r}"
    return None


def _execute_tool(name: str, args: dict, role: str) -> str:
    if name == "read_file":
        path = args.get("path", "")
        denial = _check_access(role, path)
        if denial:
            return denial
        try:
            return Path(path).read_text(encoding="utf-8")
        except FileNotFoundError:
            return f"FileNotFoundError: {path}"
        except UnicodeDecodeError:
            return f"UnicodeDecodeError: {path} is not valid UTF-8"
        except Exception as e:
            return f"Error reading {path}: {e}"

    if name == "write_file":
        path = args.get("path", "")
        denial = _check_access(role, path)
        if denial:
            return denial
        content = args.get("content", "")
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"OK: wrote {len(content)} chars to {path}"
        except Exception as e:
            return f"Error writing {path}: {e}"

    if name == "list_dir":
        path = args.get("path", ".")
        denial = _check_access(role, path)
        if denial:
            return denial
        try:
            entries = sorted(child.name for child in Path(path).iterdir())
            return "\n".join(entries) if entries else "(empty)"
        except FileNotFoundError:
            return f"DirectoryNotFoundError: {path}"
        except NotADirectoryError:
            return f"NotADirectoryError: {path}"
        except Exception as e:
            return f"Error listing {path}: {e}"

    if name == "finish":
        return "OK: round complete"

    return f"Unknown tool: {name}"


def run_local(prompt: str, role: str) -> bool:
    """Run an agentic tool-use loop against OpenRouter for one round."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY is not set.", file=sys.stderr)
        return False

    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    try:
        max_steps = int(os.environ.get("OPENROUTER_MAX_STEPS", DEFAULT_MAX_STEPS))
    except ValueError:
        max_steps = DEFAULT_MAX_STEPS

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    forbidden = ROLE_FORBIDDEN.get(role, ())
    system = (
        f"You are the {role.upper()} agent in a buyer/seller negotiation. "
        "You drive the round by calling the provided file tools. Read the "
        "files described in the user message, decide on exactly one move, "
        "write the resulting markdown file(s), then call `finish`. "
        f"Access control: you may not read or write paths under {forbidden}. "
        "All paths are relative to the project root (current working dir)."
    )

    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    print(f"[{role}] starting OpenRouter loop with model={model}")

    for step in range(1, max_steps + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
        except Exception as e:
            print(f"[{role}] OpenRouter API error: {e}", file=sys.stderr)
            return False

        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        tool_calls = msg.tool_calls or []
        if not tool_calls:
            print(f"[{role}] step {step}: no tool calls — model stopped.")
            return True

        finished = False
        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            preview = ", ".join(f"{k}={v!r}" for k, v in args.items() if k != "content")
            print(f"[{role}] step {step}: {name}({preview})")
            result = _execute_tool(name, args, role)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )
            if name == "finish":
                finished = True

        if finished:
            print(f"[{role}] finished after {step} step(s).")
            return True

    print(f"[{role}] hit max_steps={max_steps} without calling finish.", file=sys.stderr)
    return True
