---
type: intent
owner: buyer | seller
round: pre-game
created-at: <ISO-8601 timestamp>
confidence: 0.0
priority: 1            # int, 1 = highest
deadline: <ISO date or null>
red-lines:
  - "non-negotiable item 1"
  - "non-negotiable item 2"
---

# Intent

Free-form description of what this side actually wants out of the negotiation.
This file is PRIVATE — never appears in /kg-shared/.

What it captures:
- The deal you would walk away happy with.
- The deal you would walk away from.
- What "winning" looks like beyond price.

The agent reads this every round to ground its decisions. It does NOT cite this
file in any /kg-shared/ output. It MAY decide to disclose specific facts via a
signal-{n}.md, but only deliberately.
