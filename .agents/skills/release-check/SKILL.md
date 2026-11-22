---
name: release-check
description:
  Review DoukiMD semantic-release readiness and manual recovery workflow
  without publishing, tagging, or changing release state.
---

# Review DoukiMD release readiness

**Use for packaging, release, or publishing-workflow questions.** This skill
never publishes, tags, creates a release commit, or mutates release refs without
explicit authorization.

## Evidence

- `.releaserc.json`
- `pyproject.toml` and `poetry.lock`
- `doukimd.yaml`
- `docs/changelog.md`
- `.github/workflows/release.yaml`
- `.github/scripts/resume-release.sh`
- `.github/scripts/release-bin/git`
- `.github/workflows/docs.yaml`
- `.makim.yaml`

## Checklist

1. Confirm `.releaserc.json` updates:
   - `src/doukimd/__init__.py`
   - `pyproject.toml`
   - `doukimd.yaml`
   - `docs/changelog.md`
   - `poetry.lock`
2. Confirm `poetry lock && poetry build`, `poetry publish`, GitHub assets, changelog,
   and release commit remain consistent.
3. Confirm normal automation does not publish unexpectedly. The release workflow
   is manual `workflow_dispatch` on upstream `main`.
4. Inspect recovery inputs:
   - `resume_tag`
   - `allow_missing_notes`
   - `repair_notes_only`
5. Inspect release-bin Git behavior and `resume-release.sh`:
   - stable tag validation
   - upstream-main ancestry
   - deferred/default-channel Git notes
   - repeatable package/release asset publication
6. Confirm package and docs artifacts are tested before live publication.

Canonical checks:

```bash
poetry check --lock
poetry run makim tests.unit
poetry run makim tests.smoke
poetry run makim tests.linter
poetry run makim docs.build
poetry run makim package.build
poetry run makim release.dry
```

Do not run `release.ci`, resume tags, repair notes, upload assets, or publish
without explicit authorization.

## Findings

- **Blockers:** evidenced version/artifact/permission/recovery defect.
- **Non-blocking:** narrow reliability improvement.
- **Verified:** exact commands/results.
- **Unverified:** live-publish-only behavior.
