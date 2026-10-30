"""
title: Static notebook discovery, literal code, rich outputs, and references.
"""

from __future__ import annotations

import base64
import json

from pathlib import Path

import pytest

from doukimd.build import build_site, compile_site
from doukimd.errors import BuildError
from doukimd.runtime import typechecked
from doukimd.search import html_text

PNG = (
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lE'
    'QVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='
)


@typechecked
def notebook_file(
    project: Path,
    cells: list[dict[str, object]],
    metadata: dict[str, object] | None = None,
    name: str = 'lesson',
) -> Path:
    """
    title: Write a valid version four notebook without depending on a kernel.
    parameters:
      project:
        type: Path
      cells:
        type: list[dict[str, object]]
      metadata:
        type: dict[str, object] | None
      name:
        type: str
    returns:
      type: Path
    """
    path = project / 'docs' / f'{name}.ipynb'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                'nbformat': 4,
                'nbformat_minor': 4,
                'metadata': metadata or {'language_info': {'name': 'python'}},
                'cells': cells,
            }
        ),
        encoding='utf-8',
    )
    return path


@typechecked
def markdown(source: str, **extra: object) -> dict[str, object]:
    """
    title: Construct one Markdown cell in its serialized representation.
    parameters:
      source:
        type: str
      extra:
        type: object
        variadic: keyword
    returns:
      type: dict[str, object]
    """
    return {'cell_type': 'markdown', 'metadata': {}, 'source': source, **extra}


@typechecked
def code(
    source: str,
    outputs: list[dict[str, object]],
    tags: list[str] | None = None,
) -> dict[str, object]:
    """
    title: Construct a recorded code cell that must never execute.
    parameters:
      source:
        type: str
      outputs:
        type: list[dict[str, object]]
      tags:
        type: list[str] | None
    returns:
      type: dict[str, object]
    """
    return {
        'cell_type': 'code',
        'metadata': {'tags': tags or []},
        'source': source,
        'execution_count': 7,
        'outputs': outputs,
    }


@typechecked
def rich(data: dict[str, object]) -> dict[str, object]:
    """
    title: Construct one saved display result with alternate formats.
    parameters:
      data:
        type: dict[str, object]
    returns:
      type: dict[str, object]
    """
    return {'output_type': 'display_data', 'data': data, 'metadata': {}}


@typechecked
def test_notebook_pipeline_without_execution(example: Path) -> None:
    """
    title: Share templates, API refs, headings, links, navigation, and search.
    parameters:
      example:
        type: Path
    """
    lesson = notebook_file(
        example,
        [
            markdown(
                '---\ntitle: Saved lesson\nrender: jinja\n'
                'meta:\n  topic: Arrays\n'
                '---\n# {{ page.meta.topic }}\n\n## Repeated\n\n'
                'See {@api example.add}.\n\n[Home](../index.md)'
            ),
            code(
                "raise RuntimeError('must never execute')\n{{ untouched }}\n",
                [
                    {
                        'output_type': 'stream',
                        'name': 'stdout',
                        'text': ['Saved ', 'result\n'],
                    },
                    rich({'text/plain': ['answer <42> {{ unchanged }}']}),
                ],
            ),
            markdown('## Repeated\n\n::: api example.add\n:::\n'),
            {
                'cell_type': 'raw',
                'source': '<script>literal raw</script>',
                'metadata': {},
            },
        ],
        {'doukimd': {'layout': 'full'}, 'language_info': {'name': 'python'}},
        'tutorial/lesson',
    )
    original = lesson.read_bytes()
    (example / 'docs/index.md').write_text(
        '# Home\n\n[Lesson](tutorial/lesson.ipynb#repeated-1)'
    )
    config = example / 'doukimd.yaml'
    config.write_text(
        config.read_text() + 'navigation:\n  navbar:\n'
        '    - title: Tutorial\n      path: tutorial/lesson.ipynb#repeated\n'
    )
    first = build_site(config)
    second = compile_site(config)
    assert first.files == second.files
    assert lesson.read_bytes() == original
    html = first.files['tutorial/lesson.html'].decode()
    assert '<h1 id="arrays">Arrays</h1>' in html
    assert 'page-layout-full' in html
    assert 'href="../api/python/example.add.html"' in html
    assert 'href="../index.html"' in html
    assert 'id="repeated-1"' in html
    assert 'In [7]' in html and 'Saved result' in html
    assert '{{ untouched }}' in html_text(html) and '{{ unchanged }}' in html
    assert 'answer &lt;42&gt;' in html
    assert '&lt;script&gt;literal raw&lt;/script&gt;' in html
    index = json.loads(first.files['search.json'])
    lesson_entries = [
        item for item in index if item['url'].startswith('tutorial/')
    ]
    assert any(item['url'].endswith('#repeated-1') for item in lesson_entries)
    assert any('Saved result' in item['text'] for item in lesson_entries)
    assert (
        'href="tutorial/lesson.html#repeated-1"'
        in first.files['index.html'].decode()
    )


@typechecked
def test_images_html_attachments_and_mime_fallback(project: Path) -> None:
    """
    title: Render static diagrams and HTML without enabling script execution.
    parameters:
      project:
        type: Path
    """
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><text>Diagram</text><script>bad()</script></svg>'
    path = notebook_file(
        project,
        [
            markdown(
                '# Media\n\n![Attached](attachment:plot.png)',
                attachments={'plot.png': {'image/png': [PNG[:40], PNG[40:]]}},
            ),
            code(
                'plot()',
                [
                    rich({'image/png': PNG, 'text/plain': 'PNG fallback'}),
                    rich(
                        {
                            'image/svg+xml': svg,
                            'text/vnd.mermaid': 'unsupported alternative',
                        }
                    ),
                    rich(
                        {
                            'text/html': '<script>bad()</script>'
                            '<table><tr><td>Table result</td></tr></table>'
                        }
                    ),
                    rich(
                        {
                            'application/vnd.jupyter.widget-view+json': {
                                'version': 2
                            },
                            'text/plain': 'Widget fallback',
                        }
                    ),
                    rich({'application/json': {'a': [1, 2]}}),
                    rich(
                        {
                            'text/markdown': '## Output heading\n\n'
                            '[Home](index.md)'
                        }
                    ),
                    {
                        'output_type': 'error',
                        'ename': 'ValueError',
                        'evalue': 'bad',
                        'traceback': ['\u001b[31mValueError: <bad>\u001b[0m'],
                    },
                    {
                        'output_type': 'stream',
                        'name': 'stderr',
                        'text': 'warning',
                    },
                ],
            ),
        ],
    )
    result = compile_site(project / 'doukimd.yaml')
    html = result.files['lesson.html'].decode()
    assert f'src="data:image/png;base64,{PNG}"' in html
    encoded_svg = base64.b64encode(svg.encode()).decode()
    assert f'src="data:image/svg+xml;base64,{encoded_svg}"' in html
    assert '<svg' not in html and '<script>bad()' not in html
    assert 'sandbox=""' in html and 'allow-scripts' not in html
    assert 'Content-Security-Policy' in html
    assert 'srcdoc="&lt;!doctype html&gt;' in html
    assert 'Widget fallback' in html and 'notebook-output--stderr' in html
    assert 'ValueError: &lt;bad&gt;' in html and '\u001b' not in html
    assert '<h2 id="output-heading">Output heading</h2>' in html
    records = json.loads(result.files['search.json'])
    record = next(item for item in records if item['url'] == 'lesson.html')
    assert 'Table result' in record['text'] and 'Diagram' in record['text']
    assert 'bad()' not in record['text']
    assert path.read_text().startswith('{')


@typechecked
def test_removed_content_stays_out_of_page_and_search(project: Path) -> None:
    """
    title: Apply standard removal tags before rendering and search extraction.
    parameters:
      project:
        type: Path
    """
    notebook_file(
        project,
        [
            markdown('# Lesson'),
            markdown('private_cell', metadata={'tags': ['remove-cell']}),
            code(
                'private_input',
                [
                    {
                        'output_type': 'stream',
                        'name': 'stdout',
                        'text': 'visible_output',
                    }
                ],
                ['remove-input'],
            ),
            code(
                'visible_input',
                [
                    {
                        'output_type': 'stream',
                        'name': 'stdout',
                        'text': 'private_output',
                    }
                ],
                ['remove-output'],
            ),
        ],
    )
    result = compile_site(project / 'doukimd.yaml')
    combined = (
        result.files['lesson.html'].decode()
        + result.files['search.json'].decode()
    )
    for secret in ['private_cell', 'private_input', 'private_output']:
        assert secret not in combined
    assert 'visible_input' in combined and 'visible_output' in combined


@pytest.mark.parametrize(
    ('data', 'message'),
    [
        ('not json', 'notebook'),
        ('[]', 'version 4'),
        ('{"nbformat": 3}', 'version 4'),
        ('{"nbformat": 4, "nbformat_minor": 999}', 'minor version'),
        ('{"nbformat": 4, "nbformat_minor": 4, "cells": []}', 'metadata'),
    ],
)
@typechecked
def test_invalid_notebooks(project: Path, data: str, message: str) -> None:
    """
    title: Reject malformed or unsupported inputs without rewriting source.
    parameters:
      project:
        type: Path
      data:
        type: str
      message:
        type: str
    """
    path = project / 'docs/invalid.ipynb'
    path.write_text(data)
    with pytest.raises(BuildError, match=message):
        compile_site(project / 'doukimd.yaml')
    assert path.read_text() == data


@pytest.mark.parametrize(
    ('cells', 'message'),
    [
        (
            [code('x', [rich({'image/png': 'not base64!'})])],
            'Cell 1: Invalid base64',
        ),
        ([code('x', [rich({'text/html': 42})])], 'not valid under'),
        (
            [code('x', [rich({'application/javascript': 'alert(1)'})])],
            'No supported output',
        ),
        (
            [markdown('![Missing](attachment:missing.png)')],
            'Unknown image attachment',
        ),
        (
            [markdown('[Link](attachment:plot.png)')],
            'Attachments require image',
        ),
        ([markdown('[Missing](missing.ipynb)')], 'Unknown local target'),
    ],
)
@typechecked
def test_notebook_rendering_failures(
    project: Path, cells: list[dict[str, object]], message: str
) -> None:
    """
    title: Fail explicitly for unusable MIME bundles, attachments, and links.
    parameters:
      project:
        type: Path
      cells:
        type: list[dict[str, object]]
      message:
        type: str
    """
    notebook_file(project, cells)
    with pytest.raises(BuildError, match=message):
        compile_site(project / 'doukimd.yaml')


@typechecked
def test_notebook_route_collisions(project: Path) -> None:
    """
    title: Treat notebooks and Markdown as one output route namespace.
    parameters:
      project:
        type: Path
    """
    notebook_file(project, [markdown('# Notebook')], name='index')
    with pytest.raises(BuildError, match='Duplicate route'):
        compile_site(project / 'doukimd.yaml')


@typechecked
def test_notebook_footnote_ids_and_page_metadata(project: Path) -> None:
    """
    title: >-
      Keep cell footnotes distinct and respect notebook-level page metadata.
    parameters:
      project:
        type: Path
    """
    notebook_file(
        project,
        [
            markdown('# Notes\n\nFirst[^note].\n\n[^note]: First note.'),
            markdown('Second[^note].\n\n[^note]: Second note.'),
        ],
        {
            'doukimd': {
                'title': 'Notebook title',
                'sidebar': False,
                'search': False,
            }
        },
    )
    result = compile_site(project / 'doukimd.yaml')
    html = result.files['lesson.html'].decode()
    assert 'Notebook title' in html
    assert '<nav aria-label="Documentation">' not in html
    assert html.count('id="fn1"') == 1 and html.count('id="fn2"') == 1
    assert 'href="#fnref2"' in html
    assert all(
        not item['url'].startswith('lesson.html')
        for item in json.loads(result.files['search.json'])
    )
