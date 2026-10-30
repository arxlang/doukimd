"""
title: Search semantics, exclusions, configuration, and local assets.
"""

from __future__ import annotations

import json

from pathlib import Path

import pytest

from doukimd.build import compile_site
from doukimd.errors import BuildError
from doukimd.runtime import typechecked


@typechecked
def test_search_content_sections_and_exclusions(project: Path) -> None:
    """
    title: Index visible prose and code with page exclusions.
    parameters:
      project:
        type: Path
    """
    (project / 'docs/index.md').write_text(
        '---\nhtml: true\n---\n# Home\n\n'
        'A [readable label](https://example.com/not-indexed).\n\n'
        '## Arrays\n\nUseful café operations.\n\n'
        '```python\ncompiler.dispatch(value)\n```\n\n'
        '<script>hidden_script</script>\n<style>hidden_style</style>\n'
        '<div class="not_indexed_attribute">Visible HTML</div>\n\n'
        '## Arrays\n\nAnother array section.'
    )
    (project / 'docs/excluded.md').write_text(
        '---\nsearch: false\n---\n# Hidden page\n\nprivate_term'
    )
    result = compile_site(project / 'doukimd.yaml')
    records = json.loads(result.files['search.json'])
    assert {item['url'] for item in records} == {
        'index.html',
        'index.html#arrays',
        'index.html#arrays-1',
    }
    text = records[0]['text']
    assert 'readable label' in text and 'compiler.dispatch(value)' in text
    assert 'café' in text and 'Visible HTML' in text
    for hidden in [
        'hidden_script',
        'hidden_style',
        'not_indexed_attribute',
        'not-indexed',
        'private_term',
    ]:
        assert hidden not in json.dumps(records)
    assert 'excluded.html' in result.files
    assert (
        '<dialog class="search-dialog"' in result.files['index.html'].decode()
    )
    assert (
        'Search guides, notebooks, and API docs'
        in result.files['index.html'].decode()
    )
    assert b'fetch(' in result.files['search.js']


@typechecked
def test_search_configuration_and_nested_urls(example: Path) -> None:
    """
    title: Configure search and resolve assets from generated pages.
    parameters:
      example:
        type: Path
    """
    path = example / 'doukimd.yaml'
    original = path.read_text()
    path.write_text(original + 'search:\n  limit: 4\n  min_length: 3\n')
    result = compile_site(path)
    html = result.files['api/python/example.add.html'].decode()
    assert 'src="../../search.js" defer' in html
    assert 'data-index-url="../../search.json"' in html
    assert 'data-limit="4" data-min-length="3"' in html
    records = json.loads(result.files['search.json'])
    assert any(
        item['url'] == 'api/python/example.add.html#parameters'
        and 'First value.' in item['text']
        for item in records
    )
    path.write_text(original + 'search:\n  enabled: false\n')
    result = compile_site(path)
    assert (
        'search.json' not in result.files and 'search.js' not in result.files
    )
    assert 'search-dialog' not in result.files['index.html'].decode()


@pytest.mark.parametrize(
    'setting',
    [
        'limit: 0',
        'limit: 51',
        'min_length: 0',
        'min_length: 11',
        'enabled: 1',
        'unknown: true',
    ],
)
@typechecked
def test_invalid_search_settings(project: Path, setting: str) -> None:
    """
    title: Reject search settings that the frontend cannot use consistently.
    parameters:
      project:
        type: Path
      setting:
        type: str
    """
    path = project / 'doukimd.yaml'
    path.write_text(path.read_text() + f'search:\n  {setting}\n')
    with pytest.raises(BuildError, match='config'):
        compile_site(path)
