---
type: signal
owner: shared
by: buyer | seller
round: <int>
created-at: <ISO-8601 timestamp>
confidence: 1.0
intent-revealed: low | med | high
references:
  - "[Offer 2](./offer-2.md)"
---

# Signal <n> from <by>

DELIBERATE disclosure of a private fact, in the agent's own words. Use to:

- Telegraph urgency ("we'd like to close before end of quarter").
- Show flexibility ("we have some room on payment terms if pricing holds").
- Indicate a hard limit without naming the number ("we cannot exceed our
  budget envelope under any scenario").

`intent-revealed` is the agent's self-assessed disclosure level:
- **low**: vague, deniable, mostly performative.
- **med**: gives the other side useful directional info.
- **high**: explicit reveal of a private constraint or preference.

The agent must justify a `high` signal in `/sessions/round-{n}-{role}/docs/`
explaining why the strategic gain outweighs the asymmetry loss.
