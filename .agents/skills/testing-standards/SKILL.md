---
name: testing-standards
description:
  Select and reuse existing DoukiMD Python and Node tests, adding only distinct
  necessary coverage and targeted verification.
---

# Select meaningful DoukiMD test coverage

**Use whenever adding, changing, or reviewing tests.** Apply
[minimal-change](../minimal-change/SKILL.md).

## Pre-test audit

1. Search `tests/test_*.py`, `tests/search.cjs`, `tests/theme.cjs`, and existing
   fixtures for the invariant.
2. Extend the closest test if one case/assertion proves the defect.
3. Add a new test only for a distinct phase or failure mode.
4. Prefer the earliest responsible stage rather than duplicating config/API/
   rendering matrices.

## Test map

| Area | Preferred coverage |
| --- | --- |
| Config/models | `tests/test_config.py`, `tests/test_presentation.py` |
| Static API collection | `tests/test_api.py`, `tests/test_collection.py`, `tests/test_indexes.py` |
| Markdown/build/output | `tests/test_build.py`, `tests/test_filesystem.py`, `tests/test_output.py` |
| References/navigation/search | `tests/test_navigation.py`, `tests/test_indexes.py`, `tests/test_search.py` |
| Notebooks | `tests/test_notebooks.py` |
| Plugins/themes/assets | `tests/test_plugins.py`, `tests/test_theme.py`, `tests/test_presentation.py` |
| Runtime/dispatch | `tests/test_runtime.py` |
| Performance/caching | `tests/test_performance.py` |
| Release/recovery | `tests/test_release.py` |
| Frontend search/theme | `tests/search.cjs`, `tests/theme.cjs` |

## Verification

```bash
poetry run makim tests.unit
poetry run makim tests.smoke
poetry run makim tests.linter
node tests/search.cjs src/doukimd/themes/default/search.js
node tests/theme.cjs src/doukimd/themes/default/theme.js
poetry run makim all.ci
```

`tests.unit` requires 90% branch coverage. Coverage is evidence only when the
assertions prove the behavior.
