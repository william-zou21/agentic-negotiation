---
type: offer
owner: shared
by: buyer | seller
round: <int>
created-at: <ISO-8601 timestamp>
confidence: 1.0
expires-round: <int>     # null = standing offer
terms:
  - "[Price $45000](./term-price.md)"
  - "[Net 30](./term-payment.md)"
  - "[12 month SLA](./term-sla.md)"
supersedes: offer-<n-1>.md | null
---

# Offer <n> from <by>

Free-form rationale framed for the counterparty. This is what the other side
sees — strategic disclosure, not internal monologue.

What goes here:
- The terms in human language.
- Optional concession framing ("we moved 5% to demonstrate good faith").
- Optional pressure framing ("offer expires end of round 4").

What does NOT go here:
- Internal reasoning (that lives in /sessions/round-{n}-{role}/docs/).
- Red lines from /kg-{role}/intent.md (private).
- Memory of past rounds (private).
