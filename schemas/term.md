---
type: term
owner: shared
by: buyer | seller | mediator
round: <int>
created-at: <ISO-8601 timestamp>
confidence: 1.0
category: price | payment | sla | scope | timeline | warranty | exclusivity
---

# Term: <name>

A reusable, atomic deal component referenced from offers. Like wiki articles in
the original wiki-builder — one term file per concept, linked from many offers.

Example: `term-payment-net-30.md` defined once, linked from offer-1.md,
offer-3.md, signal-2.md, etc. This keeps the negotiation graph DRY and gives
the linker agent a clean cluster structure to query.

Body should define the term unambiguously so neither side can later claim
misinterpretation. Numbers explicit, dates explicit, conditions enumerated.
