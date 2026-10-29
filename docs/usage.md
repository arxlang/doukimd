# Authoring and configuration

Run `doukimd build --config doukimd.yaml` or `doukimd check`. The latter
compiles and validates without writing output. Paths are relative to the
configuration file; directory traversal and paths escaping the project are
rejected.

See the runnable project under `examples/basic`.

## Markdown and metadata

Pages under `docs/` become HTML at the same relative path. Optional YAML
front matter accepts `title`, `render` (`markdown` or `jinja`), and `meta`.
Unknown keys, duplicate keys, invalid types, and malformed YAML are errors.

Enable Jinja with `render: jinja`. Templates receive `site`, `project`,
`page`, `data`, `api`, `plugins`, and `build`. Project configuration and
front matter remain literal YAML. Content is rendered once, before Markdown
parsing. Values returned by templates are not evaluated again.

Content includes come from `includes/`. Use the `md_text` filter when
inserting a plain string into Markdown. Jinja syntax inside code fences is
still evaluated on templated pages: use Jinja raw blocks for literal examples.
Docstring prose is parsed as Markdown and never evaluated as Jinja.

The dialect includes CommonMark, tables, footnotes, API blocks, and API
references. Raw HTML is disabled in content. Python code highlighting uses
Pygments; unknown languages fall back to plain text.

## Configuration

Required settings are `site.title` and `project.name`. Defaults are
`schema_version: 1`, `docs_dir: docs`, `output_dir: build`, and
`includes_dir: includes`. Data is a mapping of names to YAML mapping files.
`project.version` is optional. `api.generate_pages` defaults to true.

An API source has `language: python`, a project-relative `root`, and
`modules` containing import paths. Configured modules and their declared
submodules, classes, and functions are collected statically. Included public
declarations require valid Douki docstrings. Explicit Douki visibility and
atpublic decorators control visibility; underscores do not imply privacy.
Literal `__all__` limits module members. Explicit re-exports and exported
standalone attributes are rejected in this version.

## API blocks and references

```markdown
::: api python:example.add
show_source: true
:::
```

API blocks accept `members: none` or `members: public` and boolean
`show_source`. The latter displays a source location, not a repository link.
`{@api python:example.add}` links to the canonical generated page.
Unknown symbols and references without a generated destination fail the build.

Generated pages live at `api/python/<qualified-name>.html`. Duplicate routes
are errors; authored overrides and canonical aliases are not implemented.
API directives inside docstrings are rejected.

When collected symbols exist and `api.generate_pages` is enabled, the engine
also generates `api/index.html` (served at `/api/`). The menu gathers all
references under **API Docs**, with nested modules, classes, and functions.
The index lists root declarations; each reference page summarizes and links
to its immediate children. Explicitly selected submodules remain visible
even when their parent module is outside the configured collection.
The bundled theme expands the active API branch and lists section anchors
under **On this page**. Disabling generated pages removes the API section.

## Links and output

Relative Markdown links are rewritten to HTML and checked after all pages
and heading anchors are known. Duplicate heading anchors get stable numeric
suffixes. Local images and downloadable files must be under `docs/assets/`.
External and site-root links are not fetched or checked.

Output includes HTML, CSS, `search.json`, `symbols.json`, and a versioned
build manifest. Search data is emitted; the bundled theme does not yet include
an interactive search UI. No generated Markdown is written into source.

DoukiMD replaces an existing output directory only when its manifest identifies
it as a managed build. A failed compilation preserves the previous output.
The output directory must not overlap documentation, source, includes, theme,
or configured data inputs.

## Themes and plugins

Set `theme.directory` to a local directory containing `page.html` to override
the bundled HTML template. Themes receive the content context plus
`content`, `navigation`, `table_of_contents`, and `stylesheet`.
Navigation entries expose `title`, relative `url`, `current` (exact route),
`active` (current route or descendant), and recursive `children`.
Table-of-contents entries expose `title`, anchor `url`, and `level` (`h2` or
`h3`). Both structures are planned by the engine and can be styled by themes.
HTML autoescaping is enabled;
only the engine-rendered content should use Jinja's `safe` filter.

Explicitly enabled `plugins` are loaded from the `doukimd.plugins` Python
entry-point group. Each entry point exposes an object with a
`@doukimd.plugins.hookimpl` method named `doukimd_context(config)` returning
a JSON-compatible mapping. Its values appear under `plugins.<plugin-name>`.
Configuration order defines invocation order. Missing plugins, unsupported
hooks, and invalid results fail the build. Plugins run trusted Python code.

## Initial boundaries

Arx collection, inherited members, dynamic Python APIs, overload sets,
automatic repository source links, incremental builds, a preview server, and
cross-project inventories are follow-up work. Arx configuration is rejected
until an adapter can consume retained frontend docstrings.
