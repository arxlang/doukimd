"""
title: Cross-phase build and template contracts.
"""

from __future__ import annotations

import json

from pathlib import Path

import pytest

from click.testing import CliRunner

from doukimd.build import MANIFEST, build_site, compile_site
from doukimd.cli import main
from doukimd.errors import BuildError
from doukimd.runtime import typechecked


@typechecked
def test_full_example_and_repeatability(example: Path) -> None:
    """
    title: Build APIs, templates, references, and stable repeat output.
    parameters:
      example:
        type: Path
    """
    path = example / 'doukimd.yaml'
    first = build_site(path)
    second = build_site(path)
    assert first.files == second.files
    assert first.page_count == 4
    index = first.files['index.html'].decode()
    assert 'Python 3.10\u20133.14' in index
    assert 'Install the package for example' in index
    assert 'href="api/python/example.add.html"' in index
    assert 'First value.' in index
    assert 'helper' not in first.files['symbols.json'].decode()
    plain = first.files['plain.html'].decode()
    assert '{{ values }}' in plain
    assert 'not_a_real_symbol' in plain
    symbols = json.loads(first.files['symbols.json'])
    assert symbols['schema_version'] == 1
    line = symbols['symbols']['python:example.add']['line']
    source = (example / 'src/example.py').read_text().splitlines()
    assert source[line - 1].strip() == '@public'
    assert json.loads(first.files[MANIFEST])['generator'] == 'doukimd'
    assert len(json.loads(first.files['search.json'])) == 4


@typechecked
def test_check_does_not_write(project: Path) -> None:
    """
    title: Validate all output without creating the target directory.
    parameters:
      project:
        type: Path
    """
    result = compile_site(project / 'doukimd.yaml')
    assert result.page_count == 1
    assert not (project / 'build').exists()
    checked = CliRunner().invoke(
        main, ['check', '--config', str(project / 'doukimd.yaml')]
    )
    assert checked.exit_code == 0
    assert 'Checked 1 pages' in checked.output


@typechecked
def test_cli_error_and_version(project: Path) -> None:
    """
    title: Surface build diagnostics and command help without tracebacks.
    parameters:
      project:
        type: Path
    """
    runner = CliRunner()
    assert runner.invoke(main, ['--help']).exit_code == 0
    assert runner.invoke(main, ['--version']).exit_code == 0
    assert runner.invoke(main, ['build', '--help']).exit_code == 0
    for command in ['build', 'check']:
        result = runner.invoke(
            main, [command, '--config', str(project / 'missing')]
        )
        assert result.exit_code == 1
        assert '[config]' in result.output
    result = runner.invoke(
        main, ['build', '--config', str(project / 'doukimd.yaml')]
    )
    assert result.exit_code == 0


@pytest.mark.parametrize(
    ('body', 'message'),
    [
        ('---\nunknown: true\n---\nHi', 'metadata'),
        ('---\ntitle: missing closing delimiter', 'Unterminated'),
        ('---\nrender: jinja\n---\n{{ page.meta.missing }}', 'template'),
        ('---\nrender: jinja\n---\n{% include "missing.md" %}', 'template'),
        ('---\nrender: jinja\n---\n{% broken %}', 'template'),
        ('::: api python:missing\n:::', 'Unknown API'),
        ('::: api python:missing', 'Unterminated API'),
        ('::: api python:missing\nunknown: 1\n:::', 'markdown'),
        ('::: api python:missing\nshow_source: "yes"\n:::', 'markdown'),
        ('See {@api python:missing}.', 'No generated API page'),
        ('[Missing](missing.md)', 'Unknown local target'),
        ('[Missing](#missing)', 'Unknown heading anchor'),
        ('![Missing](assets/missing.png)', 'Unknown local target'),
    ],
)
@typechecked
def test_build_failures_preserve_previous_output(
    project: Path, body: str, message: str
) -> None:
    """
    title: Never replace the last successful site after invalid input.
    parameters:
      project:
        type: Path
      body:
        type: str
      message:
        type: str
    """
    config = project / 'doukimd.yaml'
    before = build_site(config)
    (project / 'docs/index.md').write_text(body, encoding='utf-8')
    with pytest.raises(BuildError, match=message):
        build_site(config)
    assert (project / 'build/index.html').read_bytes() == before.files[
        'index.html'
    ]


@typechecked
def test_metadata_templates_and_escaping(project: Path) -> None:
    """
    title: Separate metadata, Markdown composition, and HTML escaping.
    parameters:
      project:
        type: Path
    """
    (project / 'doukimd.yaml').write_text(
        'site:\n  title: "<Docs>"\nproject:\n  name: test\n'
        'data:\n  info: data.yaml\n',
        encoding='utf-8',
    )
    (project / 'data.yaml').write_text(
        'value: "{{ should_not_run }}"\n', encoding='utf-8'
    )
    (project / 'includes').mkdir()
    (project / 'includes/snippet.md').write_text(
        'Included {{ project.name }}', encoding='utf-8'
    )
    (project / 'docs/index.md').write_text(
        '---\ntitle: "<Page>"\nrender: jinja\n'
        'meta:\n  label: "**literal**"\n---\n'
        '{{ page.meta.label | md_text }}\n\n'
        '{{ data.info.value }}\n\n'
        '{% include "snippet.md" %}\n\n'
        '{% raw %}{{ missing }}{% endraw %}\n',
        encoding='utf-8',
    )
    html = compile_site(project / 'doukimd.yaml').files['index.html'].decode()
    assert '&lt;Docs&gt;' in html
    assert '&lt;Page&gt;' in html
    assert '**literal**' in html
    assert '<strong>literal</strong>' not in html
    assert '{{ should_not_run }}' in html
    assert '{{ missing }}' in html
    assert 'Included test' in html


@typechecked
def test_links_anchors_assets_and_highlighting(project: Path) -> None:
    """
    title: Resolve forward page links and preserve literal fenced directives.
    parameters:
      project:
        type: Path
    """
    (project / 'docs/assets').mkdir()
    (project / 'docs/assets/logo.txt').write_text('asset', encoding='utf-8')
    (project / 'docs/nested').mkdir()
    (project / 'docs/nested/other.md').write_text(
        '---\ntitle: Other\n---\n# Repeated\n\n# Repeated\n',
        encoding='utf-8',
    )
    (project / 'docs/index.md').write_text(
        '# Home\n\n[Forward](nested/other.md?x=1#repeated-1)\n'
        '[External](https://example.com/)\n[Root](/unknown)\n'
        '![Logo](assets/logo.txt)\n'
        '\n```unknown-language\nliteral <value>\n```\n'
        '\n```python\nvalue = 1\n```\n'
        '\n```markdown\n::: api python:missing\n:::\n```\n'
        '\n    ::: api python:missing\n    :::\n',
        encoding='utf-8',
    )
    result = compile_site(project / 'doukimd.yaml')
    html = result.files['index.html'].decode()
    assert 'nested/other.html?x=1#repeated-1' in html
    assert 'id="repeated-1"' in result.files['nested/other.html'].decode()
    assert result.files['assets/logo.txt'] == b'asset'
    assert 'literal &lt;value&gt;' in html
    assert 'highlight' in html


@typechecked
def test_custom_theme_and_strict_failure(project: Path) -> None:
    """
    title: Let themes change presentation without changing API identities.
    parameters:
      project:
        type: Path
    """
    config = project / 'doukimd.yaml'
    config.write_text(
        config.read_text() + 'theme:\n  directory: theme\n',
        encoding='utf-8',
    )
    (project / 'theme').mkdir()
    theme = project / 'theme/page.html'
    theme.write_text(
        '<article>{{ page.title }}{{ content | safe }}</article>',
        encoding='utf-8',
    )
    result = compile_site(config)
    assert result.files['index.html'].startswith(b'<article>Home')
    theme.write_text('{{ missing }}', encoding='utf-8')
    with pytest.raises(BuildError, match='theme'):
        compile_site(config)


@pytest.mark.parametrize(
    'output',
    ['.', 'docs', 'docs/nested', 'includes', '../outside', '/tmp/site'],
)
@typechecked
def test_output_cannot_overlap_inputs(project: Path, output: str) -> None:
    """
    title: Reject output destinations that could overwrite project sources.
    parameters:
      project:
        type: Path
      output:
        type: str
    """
    config = project / 'doukimd.yaml'
    config.write_text(
        config.read_text() + f'output_dir: {output}\n', encoding='utf-8'
    )
    with pytest.raises(BuildError):
        build_site(config)


@typechecked
def test_unmanaged_output_is_preserved(project: Path) -> None:
    """
    title: Refuse replacement of existing user-owned files.
    parameters:
      project:
        type: Path
    """
    target = project / 'build'
    target.mkdir()
    (target / 'notes.txt').write_text('keep', encoding='utf-8')
    with pytest.raises(BuildError, match='unmanaged'):
        build_site(project / 'doukimd.yaml')
    assert (target / 'notes.txt').read_text() == 'keep'


@typechecked
def test_removed_pages_do_not_leave_stale_output(project: Path) -> None:
    """
    title: Replace the complete managed site after successful compilation.
    parameters:
      project:
        type: Path
    """
    extra = project / 'docs/extra.md'
    extra.write_text('# Extra', encoding='utf-8')
    config = project / 'doukimd.yaml'
    build_site(config)
    extra.unlink()
    build_site(config)
    assert not (project / 'build/extra.html').exists()
