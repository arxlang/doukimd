---
name: open-pr
description:
  Open or update a scoped arxlang/doukimd pull request with a Conventional
  Commit title and repository PR-template sections.
---

# Open or update a DoukiMD PR

**Use only when explicitly asked to create, push, open, or update a PR.** Apply
[minimal-change](../minimal-change/SKILL.md) and
[pr-review](../pr-review/SKILL.md). Never infer authority to merge, publish,
tag, or force-push.

## Preflight

1. Identify upstream `arxlang/doukimd`, the requested fork, branch, base, and
   head SHA.
2. Inspect `git status` and the complete branch diff.
3. Run focused tests, Node checks where relevant, and `poetry check --lock`.

## PR quality gate

- Title: Conventional Commit format, for example
  `fix(build): preserve managed output on staging failure`.
- Align body with `.github/PULL_REQUEST_TEMPLATE.md`:
  - `## Problem and resulting behavior`
  - `## Validation`
  - `## Scope`
- Include exact commands/results and limitations.
- Avoid duplicate tests, generated artifacts, lockfile hand edits, vendor
  changes, unrelated docs, or new roadmap work.

Never merge or force-push. Commit/push/open/update only with authorization.
Do not publish or recover releases as PR follow-up.

Done: report branch, base SHA, PR URL or compare URL, validation, and blockers.
