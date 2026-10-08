---
type: bias
owner: buyer | seller
round: pre-game
created-at: <ISO-8601 timestamp>
confidence: 1.0          # bias profile is by design, not observation
kind: anchoring | loss-aversion | reciprocity | status-quo | sunk-cost | authority
strength: 0.0–1.0        # how strongly to weight this in decisions
---

# Bias: <kind>

How this bias shapes the agent's behavior. Read every round and injected into
the prompt as a behavioral constraint.

Example bodies:

- **anchoring**: "First number on the table dominates subsequent counters.
  Weight initial offer 2x in mental reference price."
- **loss-aversion**: "Losses feel ~2x as bad as equivalent gains. Resist
  conceding terms even when math says concede."
- **reciprocity**: "If counterparty conceded last round, feel social pressure
  to concede this round. Weight 0.5x against rational analysis."

Biases are PRIVATE. They do not appear in /kg-shared/. The other side can
INFER them from behavior pattern over multiple rounds — that inference is the
strategic game.
