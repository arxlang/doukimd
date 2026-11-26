---
name: ci-debug
description:
  Investigate DoukiMD GitHub Actions and Makim failures by finding the first
  meaningful root failure and applying the narrowest verified fix.
---

# Diagnose DoukiMD CI failures

**Use for a failed GitHub Actions run or Makim task.** Read the exact workflow,
job, step, commit SHA, log, Python/Node version, and OS before concluding cause.

## Locate and classify

1. Identify whether the failure belongs to:
   - frontend Node 24 search/theme tests
   - Python 3.11–3.14 unit/smoke tests
   - Poetry or lockfile setup
   - pre-commit lint/type/docs quality
   - wheel/package construction or docs build
   - release/workflow permission or recovery logic
2. Compare the failing step against `.github/workflows/main.yaml`,
   `.github/workflows/docs.yaml`, `.github/workflows/release.yaml`, and
   `.makim.yaml`.
3. Baseline the commit before attributing the failure to the PR.

## Canonical verification

```bash
poetry check --lock
poetry run makim tests.unit
poetry run makim tests.smoke
poetry run makim tests.linter
poetry run makim docs.build
poetry run makim package.build
poetry run makim all.ci

node tests/search.cjs src/doukimd/themes/default/search.js
node tests/theme.cjs src/doukimd/themes/default/theme.js
```

Use the smallest failing command first. Do not lower the 90% branch coverage
gate, suppress Ruff/mypy/Douki/Bandit/Vulture/mccabe, or rerun indefinitely.

| Failure | Investigate | Avoid |
| --- | --- | --- |
| Unit/coverage | focused `tests/test_*.py`, branch coverage | deleting assertions or coverage gate |
| Smoke | CLI help and both example configurations | skipping one example |
| Lint/type | exact pre-commit hook output | unrelated formatting or broad fixes |
| Wheel | isolated venv and both examples | claiming success from source checkout |
| Frontend | Node scripts and generated assets | npm dependency installation |
| Release/docs | workflow event, source_ref, permissions | publishing or granting broad rights |

Report exact URL/job/SHA, first failure, evidence, minimal fix, commands, and
remaining unknowns.
