"""
Buyer/Seller Negotiation Sandbox

Forked from main.py. Each round is three branches: round-{n}-buyer,
round-{n}-seller, round-{n}-mediator. Each merges back to main with --no-ff
so git provenance shows who moved when.

Usage:
    uv run negotiate.py --rounds 3 --runner claude
    uv run negotiate.py --rounds 5 --runner opencode
    uv run negotiate.py --rounds 3 --runner local    # hackathon GPU run

Termination: agreement.md exists with both signed-by-* fields true, or
MAX_ROUNDS elapsed (mediator writes deadlock.md instead).
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import duckdb

from src.agents.buyer import buyer_prompt
from src.agents.seller import seller_prompt
from src.agents.mediator import mediator_prompt
from src.agents.linker import find_unlinked_clusters
from src.runner_abstract import call_agent
from src.version_control import initialize_git_repo


ROLE_DIRS = {
    "buyer": ["kg-buyer/"],
    "seller": ["kg-seller/"],
    "mediator": [],  # mediator only writes to kg-shared
}


def ensure_dirs() -> None:
    """Create all base dirs if missing."""
    for d in ("kg-shared", "kg-buyer", "kg-seller", "sessions"):
        Path(d).mkdir(exist_ok=True)


def ensure_session_workspace(round_num: int, role: str) -> str:
    """Create per-round-per-role session workspace and return its path."""
    name = f"round-{round_num}-{role}"
    base = Path("sessions", name)
    (base / "raw").mkdir(parents=True, exist_ok=True)
    (base / "processed").mkdir(exist_ok=True)
    (base / "docs").mkdir(exist_ok=True)
    return name


def stage_diff_into_raw(round_num: int, role: str) -> None:
    """Place the previous round's commit diff into this role's raw/.

    Lets the agent see exactly what the counterparty changed without giving it
    direct access to the counterparty's working files.
    """
    raw_dir = Path("sessions", f"round-{round_num}-{role}", "raw")
    diff_file = raw_dir / "previous-round-diff.txt"
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "main"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        diff_file.write_text("(no prior commits)\n")
        return
    head = result.stdout.strip()
    parent = subprocess.run(
        ["git", "log", "-1", "--format=%H", f"{head}^"],
        capture_output=True,
        text=True,
        check=False,
    )
    if parent.returncode != 0 or not parent.stdout.strip():
        diff_file.write_text("(only one commit on main)\n")
        return
    diff = subprocess.run(
        ["git", "diff", parent.stdout.strip(), head, "--", "kg-shared/"],
        capture_output=True,
        text=True,
        check=False,
    )
    diff_file.write_text(diff.stdout or "(no diff in kg-shared)\n")


def run_role_branch(round_num: int, role: str, runner: str, max_rounds: int) -> bool:
    """Create branch, run agent, commit + merge. Returns False on hard failure."""
    branch = f"round-{round_num}-{role}"
    session_name = ensure_session_workspace(round_num, role)
    stage_diff_into_raw(round_num, role)

    # Create + checkout branch off main.
    res = subprocess.run(["git", "checkout", "-b", branch], check=False)
    if res.returncode != 0:
        print(f"Failed to create branch {branch}", file=sys.stderr)
        return False

    # Build prompt.
    if role == "buyer":
        prompt = buyer_prompt(round_num, max_rounds)
    elif role == "seller":
        prompt = seller_prompt(round_num, max_rounds)
    else:  # mediator
        con = duckdb.connect()
        try:
            con.execute("INSTALL markdown FROM community; LOAD markdown;")
        except duckdb.Error:
            pass
        try:
            unlinked = find_unlinked_clusters(con)
        except Exception as e:
            print(f"  (linker query failed, mediator will run without cluster data: {e})")
            unlinked = []
        prompt = mediator_prompt(round_num, max_rounds, unlinked)

    # Invoke.
    ok = call_agent(prompt, role=role, runner=runner)
    if not ok:
        print(f"Agent [{role}] failed in round {round_num}", file=sys.stderr)
        subprocess.run(["git", "checkout", "main"], check=False)
        subprocess.run(["git", "branch", "-D", branch], check=False)
        return False

    # Stage every dir the role might have written to.
    paths_to_stage = ["kg-shared/", "sessions/", *ROLE_DIRS[role]]
    subprocess.run(["git", "add", *paths_to_stage], check=False)

    status = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=False
    )
    if not status.stdout.strip():
        print(f"  ({role} round {round_num}: no changes — agent took no action)")
        subprocess.run(["git", "checkout", "main"], check=False)
        subprocess.run(["git", "branch", "-D", branch], check=False)
        return True

    # Commit.
    commit_msg = f"round-{round_num}-{role}: agent move"
    summary_path = Path("sessions", session_name, "docs", "summary.txt")
    if summary_path.exists():
        s = summary_path.read_text().strip()
        if s:
            commit_msg = f"round-{round_num}-{role}: {s}"
    subprocess.run(["git", "commit", "-m", commit_msg], check=False)

    # Merge back to main.
    subprocess.run(["git", "checkout", "main"], check=False)
    merge = subprocess.run(
        ["git", "merge", "--no-ff", branch, "-m", f"Merge {branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if merge.returncode != 0:
        print(f"⚠ Merge conflict on {branch}:\n{merge.stderr}", file=sys.stderr)
        print("Resolve manually, then re-run from the next round.")
        return False

    subprocess.run(["git", "branch", "-d", branch], check=False)
    print(f"✓ {branch} merged into main")
    return True


def agreement_signed() -> bool:
    """True iff kg-shared/agreement.md has both signed-by-* fields true."""
    p = Path("kg-shared", "agreement.md")
    if not p.exists():
        return False
    try:
        import frontmatter
    except ImportError:
        # Fall back to crude string search if frontmatter not yet installed.
        text = p.read_text()
        return "signed-by-buyer: true" in text and "signed-by-seller: true" in text
    post = frontmatter.load(p)
    return bool(post.get("signed-by-buyer")) and bool(post.get("signed-by-seller"))


def main(rounds: int, runner: str) -> None:
    ensure_dirs()
    initialize_git_repo()

    for n in range(1, rounds + 1):
        print(f"\n{'#' * 80}\n# ROUND {n} of {rounds}\n{'#' * 80}")

        for role in ("buyer", "seller", "mediator"):
            print(f"\n── {role.upper()} ──")
            ok = run_role_branch(n, role, runner, rounds)
            if not ok:
                print(f"\nNegotiation halted at round {n} ({role}).", file=sys.stderr)
                sys.exit(1)

            if agreement_signed():
                print("\n✓ Agreement signed by both sides.")
                print("  See kg-shared/agreement.md")
                print(f"  Provenance: git log --oneline --graph")
                return

    print(f"\n{rounds} rounds completed without agreement.")
    if Path("kg-shared/deadlock.md").exists():
        print("Mediator recorded deadlock — see kg-shared/deadlock.md")
    else:
        print("No deadlock node either; mediator may not have terminated cleanly.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Buyer/Seller negotiation sandbox over a shared knowledge graph."
    )
    parser.add_argument(
        "--rounds", type=int, default=3, help="Maximum number of rounds (default: 3)."
    )
    parser.add_argument(
        "--runner",
        choices=("claude", "opencode", "local"),
        default="claude",
        help="Agent runner backend (default: claude).",
    )
    args = parser.parse_args()
    main(args.rounds, args.runner)
