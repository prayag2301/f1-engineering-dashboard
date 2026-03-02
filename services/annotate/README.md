# Service: Annotate

TypeScript LLM worker for structured upgrade extraction and callout generation.

## Queue

Consumes from: `annotate` (Redis/BullMQ)

## Responsibilities

- Read evidence rows
- Generate structured hypotheses via LLM
- Write upgrade callouts with symbolic anchors
- Compute confidence scores (outlet credibility + photo presence + cross-source agreement)
