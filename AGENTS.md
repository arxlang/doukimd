# Working on DoukiMD

- Support Python 3.10–3.14. Use strict mypy, Ruff at 79 columns, typed
  arguments, the package Typeguard wrapper, and explicit atpublic visibility.
- Use Plum dispatch for type-varying visitors with a fail-closed fallback.
- Configuration and front matter are literal, validated YAML. Jinja applies
  once to explicitly enabled page bodies. Never evaluate docstrings as Jinja.
- Keep API collection, document expansion, reference resolution, and HTML
  rendering separate. Themes cannot define symbol identities or routes.
- Collect Python statically. Reject unsupported exports and language adapters
  with structured errors; do not silently drop configured inputs.
- Read the schema shipped by Douki; never fork its schema or import private
  Douki modules. Do not modify documented source during a build.
- Keep documentation concise: authoring, configuration, supported behavior,
  and limitations. Generate reference pages instead of maintaining API prose.
- Run `poetry run makim all.ci`, `poetry check --lock`, and wheel smoke checks.
  Add focused tests at the earliest affected phase and integration coverage.
- Update manifests and run root `poetry lock`; never edit the lockfile manually.
- Never use heredocs in YAML. Release and publication workflows must remain
  explicit manual actions on upstream main.
