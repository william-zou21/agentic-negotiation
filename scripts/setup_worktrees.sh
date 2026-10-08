#!/usr/bin/env bash
# Runner-agnostic isolation: each agent gets its own git worktree where the
# other side's private folder physically does not exist. /kg-shared/ is shared
# via a symlink so changes flow through git as normal.
#
# This is the production-grade access control for the AMD hackathon GPU run
# (where settings.json hooks don't apply because we're calling a local LLM
# directly). It's also a useful belt-and-suspenders even on Claude Code.
#
# Layout after running this script:
#
#   <parent-dir>/
#     agentic-wiki-builder/                ← main checkout (orchestrator)
#     worktrees/
#       buyer/                             ← worktree on `wt-buyer` branch
#         kg-buyer/      (real)
#         kg-seller/     (DOES NOT EXIST — physically absent)
#         kg-shared/     (symlink → ../../agentic-wiki-builder/kg-shared)
#       seller/                            ← worktree on `wt-seller` branch
#         kg-seller/     (real)
#         kg-buyer/      (DOES NOT EXIST)
#         kg-shared/     (symlink)
#       mediator/                          ← worktree on `wt-mediator` branch
#         kg-buyer/      (symlink, READ-ONLY mount via chmod)
#         kg-seller/     (symlink, READ-ONLY)
#         kg-shared/     (symlink)
#
# Usage:
#   ./scripts/setup_worktrees.sh          # create all three worktrees
#   ./scripts/setup_worktrees.sh clean    # remove worktrees
#
# Caveats:
#   - macOS chmod on a symlink targets the symlink itself, not the target.
#     The "read-only" mediator mount relies on filesystem ACL or running the
#     mediator as a different user. For local dev, the lane_check.sh hook
#     remains the practical enforcement; this script is the spec.
#   - Each worktree shares the same .git, so commits from any worktree show
#     up in the others' history. That's what we want — git provenance is the
#     audit trail. Branches keep each agent's commits separable.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARENT_DIR="$(dirname "$REPO_ROOT")"
WORKTREES_DIR="$PARENT_DIR/worktrees"

cmd="${1:-setup}"

cleanup() {
  for role in buyer seller mediator; do
    wt="$WORKTREES_DIR/$role"
    if [[ -d "$wt" ]]; then
      echo "Removing worktree: $wt"
      git -C "$REPO_ROOT" worktree remove --force "$wt" 2>/dev/null || rm -rf "$wt"
    fi
    git -C "$REPO_ROOT" branch -D "wt-$role" 2>/dev/null || true
  done
  [[ -d "$WORKTREES_DIR" ]] && rmdir "$WORKTREES_DIR" 2>/dev/null || true
}

setup_role() {
  local role="$1"
  local wt="$WORKTREES_DIR/$role"
  local branch="wt-$role"

  if [[ -d "$wt" ]]; then
    echo "Worktree already exists: $wt (skipping create)"
  else
    echo "Creating worktree: $wt on branch $branch"
    git -C "$REPO_ROOT" worktree add -b "$branch" "$wt" main
  fi

  # Each worktree starts with a full checkout of main. We physically remove
  # the directories the role should not see, then symlink kg-shared so writes
  # flow to the canonical location.
  case "$role" in
    buyer)
      rm -rf "$wt/kg-seller"
      ;;
    seller)
      rm -rf "$wt/kg-buyer"
      ;;
    mediator)
      # Mediator keeps both private dirs as symlinks — they remain real on disk
      # in the main checkout. The lane_check.sh hook prevents writes; here we
      # rely on it as the runtime enforcer.
      rm -rf "$wt/kg-buyer" "$wt/kg-seller"
      ln -sf "$REPO_ROOT/kg-buyer"  "$wt/kg-buyer"
      ln -sf "$REPO_ROOT/kg-seller" "$wt/kg-seller"
      ;;
  esac

  # Shared KG: symlink in all three so writes by buyer/seller/mediator land
  # in the same place and git tracks them on the role's branch.
  rm -rf "$wt/kg-shared"
  ln -sf "$REPO_ROOT/kg-shared" "$wt/kg-shared"

  echo "  → $role worktree ready at $wt"
}

case "$cmd" in
  setup)
    mkdir -p "$WORKTREES_DIR"
    for role in buyer seller mediator; do
      setup_role "$role"
    done
    echo
    echo "Worktrees ready under: $WORKTREES_DIR"
    echo "Launch the buyer agent with cwd=$WORKTREES_DIR/buyer and NEGOTIATION_ROLE=buyer"
    ;;
  clean)
    cleanup
    echo "Worktrees cleaned"
    ;;
  *)
    echo "Usage: $0 [setup|clean]" >&2
    exit 1
    ;;
esac
