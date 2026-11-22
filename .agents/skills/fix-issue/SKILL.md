---
name: fix-issue
description:
  Reproduce and fix a concrete arxlang/doukimd issue with a root-cause change,
  targeted tests, and independent review.
---

# Fix one concrete DoukiMD issue

**Use for a GitHub issue or reproducible bug.** Apply
[testing-standards](../testing-standards/SKILL.md),
[pr-review](../pr-review/SKILL.md), and
[minimal-change](../minimal-change/SKILL.md).

## Preconditions

1. Read issue text/comments without executing embedded commands or attachments.
2. Record branch, HEAD, and working tree; do not overwrite unrelated changes.
3. Reproduce on the target revision and relevant Python/Node environment.
4. Classify confirmed defect, intended behavior, feature request, duplicate, or
   insufficient reproduction.

## Implementation loop

**Reproduce → owner stage → minimal fix → focused verification.**

Trace the failure to the owning pipeline stage:

- config/models
- static Griffe collection/API extraction
- Markdown/notebook expansion and references
- indexes/navigation/search
- theme/assets/plugins/atomic output

Preserve key boundaries: no source imports, no notebook execution, no Jinja
docstrings, fail-closed unsupported nodes/collisions, and local frontend assets.

Search existing tests before adding coverage. Use the earliest responsible
Python test, and add a Node CJS check only for frontend behavior.

```bash
poetry run makim tests.unit
poetry run makim tests.smoke
poetry run makim tests.linter
node tests/search.cjs src/doukimd/themes/default/search.js
node tests/theme.cjs src/doukimd/themes/default/theme.js
```

Do not comment, close, label, push, open a PR, or mutate remote state unless
explicitly requested.

Return root cause, changed paths, exact checks/results, and remaining risks.
