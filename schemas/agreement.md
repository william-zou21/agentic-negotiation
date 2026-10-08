---
type: agreement
owner: shared
by: mediator
round: <int>
created-at: <ISO-8601 timestamp>
confidence: 1.0
signed-by-buyer: false
signed-by-seller: false
final-offer: "[Offer N](./offer-N.md)"
terms:
  - "[Price $45000](./term-price.md)"
  - "[Net 30](./term-payment.md)"
---

# Agreement

Terminal node. Created by the mediator when both sides have indicated assent
(via signal-{n}.md with `intent-revealed: high` accepting the active offer).

Both `signed-by-buyer` and `signed-by-seller` must be true for `negotiate.py`
to terminate as success. If only one is true after `MAX_ROUNDS`, the run ends
in deadlock and the mediator writes `/kg-shared/deadlock.md` instead.

Once both are true, the agreement file is the single source of truth for the
deal. `git blame` on this file shows when each line was finalized.
