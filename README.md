# DoukiMD

Markdown documentation with first-class
[Douki](https://github.com/arxlang/douki) API references.

DoukiMD is an opinionated static documentation engine for projects using
Douki YAML docstrings. This initial version supports Python projects.

## Run from source

```console
poetry install
poetry run doukimd build --config examples/basic/doukimd.yaml
```

Open `examples/basic/build/index.html` to view the generated site.
Use `doukimd check` to validate without writing files.

## Included

- Markdown pages with validated YAML front matter.
- Opt-in Jinja in Markdown with project, page, data, and API metadata.
- Static Python API extraction and validation against Douki's shipped schema.
- Public re-exports, properties, data declarations, and callable variants.
- Named API source folders with per-page and per-block selection.
- Native API blocks, virtual API pages, and forward API references.
- Ordered navbar menus and product sidebars with source-scoped API trees.
- Page layouts, trusted HTML opt-in, local branding, and extra stylesheets.
- Local link and heading validation, assets, code highlighting, and JSON
  symbol and search inventories.
- A bundled theme, local Jinja theme overrides, and explicit context plugins.
- Safe replacement of managed output after successful builds.

See [authoring and configuration](docs/usage.md) and the complete
[example project](examples/basic).

## Initial scope

Python 3.10–3.14 is supported. Handwritten modules, classes, and callables
require valid Douki docstrings. Data declarations can use their annotations
and class-field documentation. Source code is never imported or rewritten.
Arx collection requires a future frontend documentation adapter and is
explicitly rejected today. Inherited members,
incremental builds, preview serving, and cross-project links are follow-ups.

The generated search data has no bundled interactive search UI yet.

## Development

```console
poetry run makim all.ci
poetry check --lock
```

Infrastructure is adapted from [Douki](https://github.com/arxlang/douki).
See [contributing](docs/contributing.md) for the pinned source and workflow.
