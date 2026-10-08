#!/usr/bin/env bash
# PreToolUse hook for Edit, Write, and Read.
#
# Reads the JSON event on stdin, extracts tool name and target file path, and
# rejects the tool call if it violates the negotiation lane rules for
# $NEGOTIATION_ROLE.
#
# Lane rules (mirror plan §3):
#   buyer:
#     READ:  kg-buyer/**, kg-shared/**, sessions/round-*-buyer/**
#            DENIED: kg-seller/**
#     WRITE: kg-buyer/**, sessions/round-*-buyer/**,
#            kg-shared/{offer|signal|concern|term}-*.md only if frontmatter
#            `by:` field equals "buyer"
#            DENIED: kg-seller/**, kg-shared/{links,agreement.md,deadlock.md}
#   seller:    symmetric
#   mediator:
#     READ:   everything (elevated access for compatibility analysis)
#     WRITE:  kg-shared/{links/**, agreement.md, deadlock.md},
#             sessions/round-*-mediator/**
#             DENIED: kg-buyer/**, kg-seller/**, other kg-shared/*
#
# Exit codes: 0 = allow, 2 = deny (stderr surfaced to model).

set -euo pipefail

EVENT_JSON=$(cat)

# Extract tool name and target file path.
read -r TOOL_NAME TARGET_PATH < <(printf '%s' "$EVENT_JSON" | python3 -c '
import json, sys
ev = json.load(sys.stdin)
ti = ev.get("tool_input", {})
print(ev.get("tool_name", ""), ti.get("file_path", ""))
')

ROLE="${NEGOTIATION_ROLE:-unset}"

if [[ -z "$TARGET_PATH" ]]; then
  exit 0
fi

PROJECT_ROOT=$(pwd)
REL_PATH="${TARGET_PATH#"$PROJECT_ROOT/"}"

deny() {
  printf 'lane_check: DENY [role=%s tool=%s] %s — %s\n' \
    "$ROLE" "$TOOL_NAME" "$REL_PATH" "$1" >&2
  exit 2
}

# Sessions/ access always permitted (path itself segments roles).
if [[ "$REL_PATH" == sessions/* ]]; then
  exit 0
fi

if [[ "$ROLE" == "unset" ]]; then
  deny "NEGOTIATION_ROLE env var not set; refusing on principle"
fi

# ── READ rules ──────────────────────────────────────────────────────────────
if [[ "$TOOL_NAME" == "Read" ]]; then
  case "$ROLE" in
    buyer)
      if [[ "$REL_PATH" == kg-seller/* ]]; then
        deny "buyer cannot read kg-seller (information asymmetry)"
      fi
      ;;
    seller)
      if [[ "$REL_PATH" == kg-buyer/* ]]; then
        deny "seller cannot read kg-buyer (information asymmetry)"
      fi
      ;;
    mediator)
      # Mediator has elevated read access — fall through.
      :
      ;;
    *)
      deny "unknown role $ROLE"
      ;;
  esac
  exit 0
fi

# ── WRITE / EDIT rules ──────────────────────────────────────────────────────
extract_by_field() {
  printf '%s' "$EVENT_JSON" | python3 -c '
import json, sys, re
ev = json.load(sys.stdin)
ti = ev.get("tool_input", {})
content = ti.get("content") or ti.get("new_string") or ""
m = re.search(r"^---\s*$(.*?)^---\s*$", content, re.MULTILINE | re.DOTALL)
if not m:
    print("")
    sys.exit(0)
for line in m.group(1).splitlines():
    line = line.strip()
    if line.startswith("by:"):
        print(line.split(":", 1)[1].strip())
        sys.exit(0)
print("")
'
}

case "$ROLE" in
  buyer)
    if [[ "$REL_PATH" == kg-seller/* ]]; then
      deny "buyer cannot write to kg-seller"
    fi
    if [[ "$REL_PATH" == kg-shared/links/* \
       || "$REL_PATH" == kg-shared/agreement.md \
       || "$REL_PATH" == kg-shared/deadlock.md ]]; then
      deny "kg-shared/{links,agreement.md,deadlock.md} are mediator-only"
    fi
    if [[ "$REL_PATH" == kg-shared/* ]]; then
      BY_FIELD=$(extract_by_field)
      if [[ -n "$BY_FIELD" && "$BY_FIELD" != "buyer" ]]; then
        deny "frontmatter by:$BY_FIELD does not match role buyer"
      fi
    fi
    ;;
  seller)
    if [[ "$REL_PATH" == kg-buyer/* ]]; then
      deny "seller cannot write to kg-buyer"
    fi
    if [[ "$REL_PATH" == kg-shared/links/* \
       || "$REL_PATH" == kg-shared/agreement.md \
       || "$REL_PATH" == kg-shared/deadlock.md ]]; then
      deny "kg-shared/{links,agreement.md,deadlock.md} are mediator-only"
    fi
    if [[ "$REL_PATH" == kg-shared/* ]]; then
      BY_FIELD=$(extract_by_field)
      if [[ -n "$BY_FIELD" && "$BY_FIELD" != "seller" ]]; then
        deny "frontmatter by:$BY_FIELD does not match role seller"
      fi
    fi
    ;;
  mediator)
    if [[ "$REL_PATH" == kg-buyer/* || "$REL_PATH" == kg-seller/* ]]; then
      deny "mediator has read-only access to private KGs"
    fi
    if [[ "$REL_PATH" == kg-shared/* ]]; then
      if ! [[ "$REL_PATH" == kg-shared/links/* \
           || "$REL_PATH" == kg-shared/agreement.md \
           || "$REL_PATH" == kg-shared/deadlock.md ]]; then
        deny "mediator can only write to kg-shared/{links/**,agreement.md,deadlock.md}"
      fi
    fi
    ;;
  *)
    deny "unknown role $ROLE"
    ;;
esac

exit 0
