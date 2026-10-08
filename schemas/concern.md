---
type: concern
owner: shared
by: buyer | seller
round: <int>
created-at: <ISO-8601 timestamp>
confidence: 1.0
severity: low | med | high | blocking
about:
  - "[Offer 3](./offer-3.md)"
  - "[Net 30](./term-payment.md)"
---

# Concern: <topic>

A stated objection or worry about a term or offer. Visible to both sides.

Severity guide:
- **low**: cosmetic, unlikely to block deal.
- **med**: would prefer addressed but not a dealbreaker.
- **high**: significant friction; if not addressed, walking is plausible.
- **blocking**: deal cannot close until this is resolved.

The mediator uses concerns to detect deadlock — if the same `blocking` concern
appears across N consecutive rounds with no offer movement, flag impasse.
