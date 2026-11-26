---
name: pr-review
description:
  Review DoukiMD PRs or local diffs for correctness, scope, test quality,
  source safety, and atomic output. Read-only unless review submission or
  editing is explicitly authorized.
---

# Review a DoukiMD pull request

**Use for PR, branch, or local-diff review.** It is read-only unless the user
explicitly requests code edits or submission of a GitHub review. Apply
[minimal-change](../minimal-change/SKILL.md).

## Inputs and scope

- Inspect exact base/head SHAs, diff, commits, body, comments, review comments,
  and CI for PR review.
- For local work, inspect `git status`, staged changes, and uncommitted changes
  separately.
- Never claim CI or coverage passed without actual results.

## Read and reason

1. State the intended contract and affected pipeline stage.
2. Trace config/models, static collection/API, content/notebooks, indexes/
   references/navigation/search, and theme/assets/plugins/output.
3. Probe static-source boundaries, Douki annotation-first schema, Jinja scope,
   notebook execution, collisions, path confinement, symlinks, unsupported
   nodes, vendor assets, and managed-output rollback.
4. Compare tests against existing Python and Node coverage.
5. Check scope: unrelated formatting, generated docs, lockfile edits, vendor
   changes, new CI, and roadmap additions.

## Severity

- P0/P1: source execution/import, notebook execution, secret exposure,
  destructive output, schema misuse, or unsafe path escape.
- P2: reproducible build/navigation/search/notebook regression or essential
  missing test.
- Non-blocking: maintainability or scope reduction not affecting correctness.

Each finding needs location, impact, evidence, and minimal correction.

```markdown
## Blocking findings

- [P1] <finding> — path:line Contract / impact / evidence / correction

## Non-blocking

- <only useful follow-up>

## Verification and uncertainties

- Confirmed: <actual evidence>
- Not verified: <specific risk>

## Recommendation

Request changes / No blockers / Unable to conclude
```

Do not post, label, or modify the PR without explicit authorization.
