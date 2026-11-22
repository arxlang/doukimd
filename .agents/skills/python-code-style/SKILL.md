---
name: python-code-style
description: >-
  Apply DoukiMD Python conventions: strict typing, atpublic, package
  @typechecked, Plum dispatch, Ruff, Douki, and security-quality tooling.
---

# Python implementation conventions for DoukiMD

**Use for Python edits and reviews.** Apply
[minimal-change](../minimal-change/SKILL.md).

## Visibility and runtime checking

- Use explicit `@public` / `@private` decorators from `atpublic`.
- Import `@typechecked` from `doukimd.runtime`, never raw `typeguard.typechecked`.
- The package wrapper checks all bound arguments and collection items, and
  checks returns.
- Annotate every argument and return. Strict mypy checks `src/doukimd`.
- Use Plum dispatch for type-varying visitors. Every dispatch should include a
  typed or fail-closed fallback.

```python
from public import public

from doukimd.errors import BuildError
from doukimd.runtime import typechecked

@public
@typechecked
def require_name(name: str) -> str:
    """
    title: Validate a required name.
    parameters:
      name:
        description: Name supplied by the caller.
    returns:
      description: Validated, non-empty name.
    """
    if not name:
        raise BuildError('config', 'Name cannot be empty')
    return name
```

## Formatting and quality

- Ruff line length 79, single quotes.
- Ruff lint: `E,F,YTT,RUF,I,UP006,UP007`.
- Ruff format check in pre-commit.
- Strict mypy on `src/doukimd`.
- Bandit: `bandit -q -r src -c pyproject.toml -iii -lll`.
- Vulture: minimum confidence 80; ignore `@hookimpl` and `@hookspec`.
- mccabe: flags cyclomatic complexity >= 20 on `src/`
  (`python -m mccabe --min 20`).
- Douki: `douki check`; it rejects legacy YAML `type:` fields.

## Control flow and errors

- Prefer validation-first guard clauses and explicit `BuildError` phases.
- Keep config, collection, rendering, filesystem, and plugin failures at their
  owning boundaries.
- Never import or execute user modules during static collection; no notebook execution and no Jinja
  evaluation of docstrings.
- Do not use broad exception catches or reflective code when typed contracts
  already exist.

## Verification

```bash
poetry run makim tests.unit
poetry run makim tests.linter
poetry run douki check src tests examples/basic/src
poetry check --lock
```
