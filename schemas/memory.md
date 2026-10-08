---
type: memory
owner: buyer | seller
round: <int>
created-at: <ISO-8601 timestamp>
confidence: 0.0          # 0.0 = guess, 1.0 = directly observed
source: round-N | pre-game
decay: 1.0               # 0.0 = forgotten, 1.0 = fully retained
topic: counterparty-tone | price-history | concession-pattern | trust-event
---

# Memory: <topic>

What did I observe, and what do I infer from it?

Examples:
- "In round 2 they conceded $3k after I mentioned my deadline. They may be more
  flexible than they let on."
- "Their language got formal in round 3 — possible loss of rapport."
- "They mentioned a competitor by name. May be using BATNA pressure."

Memories are PRIVATE. Each side maintains its own. They inform but do not
appear in /kg-shared/. The mediator can read but does not echo them back into
shared.
