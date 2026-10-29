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

The bundled theme uses Bootstrap by default. Configure presentation under
`theme`:

```yaml
theme:
  framework: bootstrap
  color_mode: auto
  palette: terracotta
```

`framework` accepts `bootstrap` or `none`; the latter omits Bootstrap for
custom themes. Bootstrap 5.3.8 CSS and its license are bundled locally.
Builds and readers do not need a CDN, npm, or Bootstrap JavaScript.
The built-in layout and appearance controls also work with `none`.

`color_mode` accepts `auto` (the system preference), `light`, or `dark`.
Readers can change Appearance in the header; their choice overrides the
configured default and is saved per project when browser storage is available.
System mode follows subsequent OS preference changes. Without JavaScript,
the configured light/dark mode is used; `auto` falls back to light.
Navigation stays usable without JavaScript, including on mobile.

`palette` accepts five presets: `terracotta` (the default), `ocean`, `forest`,
`violet`, and `slate`. Each has light and dark colors and works with either
framework setting. Readers can change Palette in the header independently
of Appearance; both choices persist per project when storage is available.
Invalid saved values fall back to configuration. Without JavaScript, the
configured palette still applies.

Terracotta keeps DoukiMD's original colors. The other four presets use
[Radix Colors](https://www.radix-ui.com/colors) 3.0.0 scales under the MIT
license, bundled with their attribution. They require no Radix components,
npm package, or network access. Body text, muted text, links, and active
navigation colors are checked at 4.5:1 or better against their backgrounds.
API-kind colors stay consistent across palettes.

API labels identify modules, classes, functions, and methods in navigation
and declaration headings. Method kinds are collected from class parentage,
including static and class methods. Labels use text as well as color.

Set `theme.directory` to a local directory containing `page.html` to override
the bundled HTML template. Themes receive the content context plus
`content`, `navigation`, `table_of_contents`, and `stylesheet`.
Navigation entries expose `title`, relative `url`, `kind` (null for authored
pages), `current` (exact route),
`active` (current route or descendant), and recursive `children`.
Table-of-contents entries expose `title`, anchor `url`, and `level` (`h2` or
`h3`). Both structures are planned by the engine and can be styled by themes.
HTML autoescaping is enabled;
only the engine-rendered content should use Jinja's `safe` filter.

Templates also receive `theme` settings, `palettes` (supported preset names),
`home_url`, `theme_script`, and
`framework_stylesheet` (null for `none`). Load the optional framework CSS
before `stylesheet`. The `page` object includes its API `identifier` and
`kind`, both null for authored pages. Symbol kinds are also in `symbols.json`.

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
