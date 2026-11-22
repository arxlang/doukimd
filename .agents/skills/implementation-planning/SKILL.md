---
name: implementation-planning
description:
  Plan feasible DoukiMD implementations or refactors with small acceptance-driven steps and existing verification.
---

# Plan a reviewable DoukiMD implementation

**Use for plans, milestones, feature breakdowns, or substantial refactoring.**
For a straightforward fix, a formal plan is unnecessary. Apply
[minimal-change](../minimal-change/SKILL.md).

## Planning protocol

1. **Goal:** State precisely what changes for users or contributors.
2. **Current implementation:** Inspect the relevant pipeline phase and existing
   tests before proposing changes.
3. **Acceptance criteria:** List 2–5 observable behaviors, including
   collision/error semantics and source safety.
4. **Smallest vertical slice:** Include only necessary stage changes:
   config/models → collection/API → content/references/navigation/search →
   theme/assets/plugins/output.
5. **Execution:** 3–7 ordered implementation outcomes.
6. **Verification:** Name exact Python and Node checks, 90% branch coverage, and
   wheel smoke where exports/package behavior changes.
7. **Risks/out of scope:** Include only real blockers and explicitly exclude
   incremental builds, preview serving, cross-project links, Arx collection,
   and interactive notebook widgets.

## Output format

```markdown
## Goal

<one sentence>

## Acceptance criteria

- <observable behavior>

## Implementation

1. <pipeline owner and change>
2. <necessary integration>
3. <existing verification>

## Risks / out of scope

<only meaningful items>
```
