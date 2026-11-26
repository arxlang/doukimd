# Working on DoukiMD

## Repository snapshot

- Package: `doukimd`, a static Markdown and notebook documentation generator.
- Python: `>=3.11,<4`; CI tests Python 3.11–3.14 on Ubuntu, macOS, and Windows.
- Runtime dependencies include Douki `>=0.14.1`, Griffe, Pydantic, MarkdownIt,
  Jinja, nbformat, pluggy, atpublic, typeguard, and Plum dispatch.
- Build backend: Poetry Core. Ruff uses 79 columns and single quotes; strict
  mypy checks `src/doukimd`.
- The frontend uses Node 24 in CI; release tooling uses Node 22.

## Architecture and pipeline invariants

- **Config/models:** `config.py` and `models.py` load strict, JSON-compatible
  YAML and Pydantic models. Configuration paths must stay inside the project.
- **Static collection:** `collection.py` and `api.py` use Griffe to collect
  Python without importing user source. Validate aliases, exports, inherited
  class field annotations, callable variants, and Douki 0.14+
  annotation-first documentation.
- **Content/rendering:** `content.py`, `notebooks.py`,
  `notebook_models.py`, `notebook_rendering.py`, `markdown.py`, and `html.py`
  discover and expand pages, render nbformat-4 notebooks, parse Markdown, and
  process trusted HTML.
- **Indexes/references/navigation/search:** `indexes.py`, `references.py`,
  `navigation.py`, `navigation_plan.py`, and `search.py` resolve API symbols,
  routes, sidebars, navbar links, and local search records.
- **Theme/output:** `theme.py`, `themes/default/`, `assets.py`, `plugins.py`,
  `output.py`, and `build.py` produce bundled theme assets, explicit plugin
  context, and staged/atomic managed output.
- Never import user source during collection or execute notebook kernels.
- Never evaluate docstrings as Jinja. Never fork or rewrite Douki's shipped
  schema. Documentation source may be read but must not be modified by builds.
- Jinja applies once to explicitly enabled page bodies and to theme templates.
- Themes cannot define API identities or routes.
- Reject unsupported exports, unsupported language adapters, unsupported
  notebook nodes, collisions, unknown targets, and unsafe paths with
  `BuildError(phase, message, source)`.
- Keep vendor Bootstrap and Radix assets local; do not add network dependencies.
- Do not add incremental builds, preview serving, cross-project links, Arx
  collection, or interactive notebook widgets unless explicitly requested.

## Code conventions

- Use typed arguments and strict mypy.
- Use explicit `@public` / `@private` from `atpublic`.
- Use the package-wide `@typechecked` wrapper from `doukimd.runtime`, not raw
  Typeguard decorators.
- Use Plum dispatch for type-varying visitors with explicit fail-closed
  fallbacks.
- Ruff uses 79 columns, single quotes, and
  `E,F,YTT,RUF,I,UP006,UP007`.
- Bandit is strict, Vulture has 80% minimum confidence and ignores
  `@hookimpl`/`@hookspec`, and mccabe flags cyclomatic complexity >= 20 on
  `src/` (`python -m mccabe --min 20`).
- Keep documentation concise and generate API pages rather than duplicating
  API prose.

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

poetry run douki check src tests examples/basic/src
```

`tests.unit` requires 90% branch coverage. `all.ci` runs unit, smoke, lint,
docs, and package builds. `makim tests.smoke` covers the basic and notebook
examples. Wheel smoke checks install `dist/*.whl` in a fresh venv and check both
example configurations.

## Release and publication

Never use heredocs in YAML. Normal pull-request/release checks must not publish.
Release publication is an explicit manual `workflow_dispatch` on upstream
`main`; use `release.dry` for inspection and `release.ci` only with explicit
authorization.

Update manifests and run `poetry lock`; never edit `poetry.lock` manually.

## Reusable Agent Skills

| Skill | Use |
| --- | --- |
| [agent-authoring](.agents/skills/agent-authoring/SKILL.md) | Add or maintain repository-local agent skills |
| [api-design](.agents/skills/api-design/SKILL.md) | Design Python APIs and CLI/config contracts |
| [ci-debug](.agents/skills/ci-debug/SKILL.md) | Diagnose GitHub Actions and Makim failures |
| [douki-docstrings](.agents/skills/douki-docstrings/SKILL.md) | Maintain annotation-first Douki docstrings |
| [fix-issue](.agents/skills/fix-issue/SKILL.md) | Reproduce and fix concrete defects |
| [implementation-planning](.agents/skills/implementation-planning/SKILL.md) | Produce reviewable implementation plans |
| [minimal-change](.agents/skills/minimal-change/SKILL.md) | Default scope-control procedure |
| [open-pr](.agents/skills/open-pr/SKILL.md) | Create or update a scoped pull request |
| [pr-review](.agents/skills/pr-review/SKILL.md) | Review PRs and local diffs |
| [python-code-style](.agents/skills/python-code-style/SKILL.md) | Python implementation conventions |
| [release-check](.agents/skills/release-check/SKILL.md) | Review release readiness without publishing |
| [testing-standards](.agents/skills/testing-standards/SKILL.md) | Select the smallest meaningful test coverage |
| [triage-issues](.agents/skills/triage-issues/SKILL.md) | Classify and route issues safely |

Apply [minimal-change](.agents/skills/minimal-change/SKILL.md) and
[implementation-planning](.agents/skills/implementation-planning/SKILL.md) to
normal implementation and planning work. Skills supplement, rather than replace,
the repository rules above.
