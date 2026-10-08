"""
Runner-agnostic agent invocation.

Wraps the existing opencode subprocess pattern in `src/agents/runner.py:12`
so the same negotiate.py round loop can target:

- "claude"   : Claude Code CLI (`claude -p <prompt>`), pinned to claude-haiku-5-5.
               Uses .claude/negotiation-settings.json + PreToolUse hook for lane enforcement.
- "opencode" : Original wiki-builder runner. No settings.json hook; relies on
               worktree isolation (scripts/setup_worktrees.sh) for access control.
- "local"    : Direct LLM call via OpenRouter (Llama by default). See
               src/runners/openrouter_runner.py. Honors role-based access
               control inline rather than relying on a PreToolUse hook.

The `role` argument sets `NEGOTIATION_ROLE` env var so the lane-check hook (or
a worktree wrapper) can identify which agent is making tool calls.
"""

import os
import subprocess
import sys


SUPPORTED_RUNNERS = ("claude", "opencode", "local")

CLAUDE_MODEL = "claude-haiku-5-5"
NEGOTIATION_SETTINGS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".claude", "negotiation-settings.json",
)


def call_agent(prompt: str, role: str, runner: str = "claude") -> bool:
    """Invoke an agent with the given prompt, identified by role.

    Args:
        prompt:  Full prompt text.
        role:    "buyer" | "seller" | "mediator". Used by the access-control
                 hook to decide write permissions.
        runner:  Which backend to use. See module docstring.

    Returns:
        True on success (returncode 0), False otherwise.
    """
    if runner not in SUPPORTED_RUNNERS:
        raise ValueError(f"Unknown runner: {runner!r}. Pick from {SUPPORTED_RUNNERS}.")

    if role not in ("buyer", "seller", "mediator"):
        raise ValueError(f"Unknown role: {role!r}.")

    print("\n" + "=" * 80)
    print(f"AGENT [{role}] via {runner}")
    print("=" * 80)
    print(prompt)
    print("=" * 80 + "\n")

    env = os.environ.copy()
    env["NEGOTIATION_ROLE"] = role

    if runner == "local":
        from src.runners.openrouter_runner import run_local
        os.environ["NEGOTIATION_ROLE"] = role
        return run_local(prompt, role)

    if runner == "claude":
        # `claude -p <prompt>` runs Claude Code in non-interactive mode. The
        # negotiation settings file carries the PreToolUse lane-check hook that
        # fires on every Edit/Write/Read call.
        cmd = [
            "claude", "-p", prompt,
            "--settings", NEGOTIATION_SETTINGS,
            "--model", CLAUDE_MODEL,
        ]
    elif runner == "opencode":
        # Original wiki-builder pattern — see src/agents/runner.py:12.
        cmd = ["opencode", "run", prompt]

    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        print(
            f"Agent [{role}] failed with returncode {result.returncode}",
            file=sys.stderr,
        )
        return False

    return True
