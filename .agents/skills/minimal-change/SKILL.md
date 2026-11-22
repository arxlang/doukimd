---
name: minimal-change
description:
  Keep DoukiMD changes and PRs minimal without compromising correctness,
  coverage, source safety, or atomic output.
---

# Minimal necessary change

**Use for every implementation, plan, test, review, and documentation task.**

## First establish the change

1. Read the request and current behavior; distinguish explicitly requested work
   from speculative improvements.
2. Inspect only relevant modules, tests, examples, Makim tasks, and workflows.
3. Reuse existing Pydantic, Griffe, MarkdownIt, Jinja, index, navigation, and
   staged-output patterns.
4. Identify the smallest existing test or Node check that proves the behavior.

## Decision table

| Proposed change | Normally do | Expand only when |
| --- | --- | --- |
| Rename | Preserve it | Meaning or correctness requires it |
| Restructure | Keep local structure | A stage boundary prevents correctness |
| Add helper | Reuse direct code | Real callers need it |
| Add test | Search existing tests first | A distinct invariant is uncovered |
| Add docs | Update existing guide only | Public behavior needs it |
| Change CI/dependency | Avoid | Delivery or verification requires it |

## Invariants

- Never import user source; never execute notebook kernels.
- Never evaluate docstrings as Jinja.
- Keep vendor assets local and theme routes out of theme code.
- Keep 90% branch coverage and fail closed on unsupported input/collisions.
- Do not add incremental builds, preview serving, cross-project links, Arx
  collection, or interactive notebook widgets unless requested.
- Preserve atomic managed output and `.doukimd-manifest.json` behavior.

Stop when the requested behavior works and relevant checks pass or blockers are
explicit. Remove incidental formatting, docs, and tooling.
