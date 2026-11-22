---
name: api-design
description:
  Design minimal, consistent DoukiMD Python, Click, Pydantic, Markdown, and
  theme APIs with clear typing and package exports.
---

# Design one coherent DoukiMD API

**Use for public Python functions/classes, CLI commands/options, Pydantic
models, API directives, plugins, themes, or output contracts.** Apply
[minimal-change](../minimal-change/SKILL.md) and
[python-code-style](../python-code-style/SKILL.md).

## API design steps

1. Find the nearest comparable implementation and trace its real callers:
   - config/models: `config.py`, `models.py`
   - collection/API: `collection.py`, `api.py`
   - content: `content.py`, `markdown.py`, `notebooks.py`,
     `notebook_rendering.py`
   - resolution/UI: `indexes.py`, `references.py`, `navigation*.py`, `search.py`
   - output: `theme.py`, `assets.py`, `plugins.py`, `output.py`, `build.py`
2. Write the common usage and one meaningful invalid/boundary case.
3. Choose one canonical call shape. Keep CLI parsing in `cli.py`, Pydantic
   validation in `models.py`/`config.py`, static collection in `collection.py`,
   and rendering in the owning stage.
4. Specify inputs, defaults, outputs, errors, source paths, routes, ownership,
   and unsupported behavior. Use `BuildError(phase, message, source)` for
   site-building failures.
5. Preserve API export visibility with `@public` / `@private` and explicit
   `__all__` behavior where used.
6. Never import user source during collection, execute notebook kernels,
   evaluate docstrings as Jinja, or silently accept unsupported declarations.

## Anti-patterns

| Avoid | Prefer |
| --- | --- |
| Validation spread across rendering | Validation in `config.py`, `models.py`, or collection |
| Theme-defined routes or API identity | `content.py`/`build.py` route planning |
| Hidden YAML `type:` fields | Python annotations plus prose Douki fields |
| Broad `Any` and generic exceptions | Typed models and phase-specific `BuildError` |
| Alias-heavy public wrappers | Existing canonical function or command |

Verify common and distinct boundary behavior in existing tests. Run:

```bash
poetry run makim tests.unit
poetry run makim tests.linter
poetry check --lock
```
