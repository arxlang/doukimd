"""
title: Generated API entry points, hierarchy, and navigation behavior.
"""

from __future__ import annotations

import re

from pathlib import Path

import pytest

from doukimd.api import collect_api
from doukimd.build import compile_site
from doukimd.config import load_config
from doukimd.content import discover_pages, plan_pages
from doukimd.errors import BuildError
from doukimd.navigation import build_navigation
from doukimd.runtime import typechecked


@typechecked
def test_api_index_and_member_summaries(example: Path) -> None:
    """
    title: Link API roots and immediate children through the generated index.
    parameters:
      example:
        type: Path
    """
    source = example / 'src/example.py'
    source.write_text(
        source.read_text() + '\nclass Counter:\n'
        '    """title: Count calls."""\n'
        '    def increment(self, amount: int = 1) -> int:\n'
        '        """\n'
        '        title: Increment the counter.\n'
        '        parameters:\n'
        '          amount:\n'
        '            type: int\n'
        '            default: 1\n'
        '            description: How many.\n'
        '        """\n'
        '        return amount\n',
        encoding='utf-8',
    )
    result = compile_site(example / 'doukimd.yaml')
    index = result.files['api/index.html'].decode()
    main = index.partition('<main id="content">')[2].partition('</main>')[0]
    assert '<h1>API Docs</h1>' in main
    assert 'href="python/example.html"' in main
    assert 'Example API' in main
    module = result.files['api/python/example.html'].decode()
    main = module.partition('<main id="content">')[2].partition('</main>')[0]
    assert '<h2 id="classes">Classes</h2>' in main
    assert '<h2 id="functions">Functions</h2>' in main
    assert 'href="example.Counter.html"' in main
    assert 'href="example.add.html"' in main
    assert 'Count calls.' in main
    counter = result.files['api/python/example.Counter.html'].decode()
    assert '<h2 id="methods">Methods</h2>' in counter
    assert 'href="example.Counter.increment.html"' in counter
    method = result.files['api/python/example.Counter.increment.html'].decode()
    assert '<strong>amount</strong>' in method
    assert '<strong>Type:</strong> int' in method
    assert '<strong>Default:</strong> 1' in method
    assert 'How many.' in method
    assert 'href="#parameters"' in method


@typechecked
def test_navigation_groups_symbols_and_uses_routes(example: Path) -> None:
    """
    title: Keep duplicate titles distinct and expand only the active branch.
    parameters:
      example:
        type: Path
    """
    (example / 'docs/duplicate.md').write_text(
        '---\ntitle: add\n---\nAn unrelated page.', encoding='utf-8'
    )
    config = load_config(example / 'doukimd.yaml')
    inventory = collect_api(example, config)
    pages = discover_pages(example, config)
    plan_pages(pages, inventory, config)
    current = next(
        page for page in pages if page.symbol == 'python:example.add'
    )
    navigation = build_navigation(pages, current, inventory)
    assert len(navigation) == 4
    duplicate = next(item for item in navigation if item.title == 'add')
    assert not duplicate.current
    api = navigation[-1]
    assert api.title == 'API Docs'
    assert api.url == '../'
    assert api.active and not api.current
    module = api.children[0]
    assert module.title == 'example'
    assert module.active and not module.current
    function = module.children[0]
    assert function.current and function.active
    assert function.url == 'example.add.html'
    result = compile_site(example / 'doukimd.yaml')
    html = result.files[current.route].decode()
    nav = html.partition('<nav aria-label="Documentation">')[2]
    nav = nav.partition('</nav>')[0]
    assert nav.count('API Docs</span>') == 1
    assert nav.count(' aria-current="page"') == 1
    assert nav.count('<details class="sidebar-group" open>') == 2
    assert re.search(r'href="example.add.html" aria-current="page"', nav)


@typechecked
def test_api_directory_links(example: Path) -> None:
    """
    title: Serve and link the generated reference at the API directory URL.
    parameters:
      example:
        type: Path
    """
    (example / 'docs/index.md').write_text(
        '# Home\n\n[Reference](api/#modules)', encoding='utf-8'
    )
    result = compile_site(example / 'doukimd.yaml')
    assert 'href="api/"' in result.files['index.html'].decode()
    assert 'href="api/#modules"' in result.files['index.html'].decode()
    assert 'api/index.html' in result.files


@typechecked
def test_selected_submodule_is_an_api_root(example: Path) -> None:
    """
    title: Preserve nested modules when their package is not selected.
    parameters:
      example:
        type: Path
    """
    package = example / 'src/package'
    package.mkdir()
    (package / '__init__.py').write_text(
        '"""title: Package."""', encoding='utf-8'
    )
    (package / 'nested.py').write_text(
        '"""title: Selected nested module."""', encoding='utf-8'
    )
    config = example / 'doukimd.yaml'
    config.write_text(
        config.read_text().replace('[example]', '[package.nested]'),
        encoding='utf-8',
    )
    (example / 'docs/index.md').write_text('# Home', encoding='utf-8')
    result = compile_site(config)
    assert (
        'python/package.nested.html' in result.files['api/index.html'].decode()
    )
    assert 'API Docs</span>' in result.files['index.html'].decode()


@pytest.mark.parametrize('route', ['index.md', 'INDEX.md'])
@typechecked
def test_api_index_collisions_fail(example: Path, route: str) -> None:
    """
    title: Reject authored collisions with the reserved generated API index.
    parameters:
      example:
        type: Path
      route:
        type: str
    """
    (example / 'docs/api').mkdir()
    (example / 'docs/api' / route).write_text('# Mine', encoding='utf-8')
    with pytest.raises(BuildError, match='Duplicate route'):
        compile_site(example / 'doukimd.yaml')


@typechecked
def test_no_generated_api_menu_without_pages(example: Path) -> None:
    """
    title: Omit the generated entry point when page generation is disabled.
    parameters:
      example:
        type: Path
    """
    config = example / 'doukimd.yaml'
    config.write_text(
        config.read_text().replace(
            'api:\n', 'api:\n  generate_pages: false\n'
        ),
        encoding='utf-8',
    )
    (example / 'docs/index.md').write_text('# Home', encoding='utf-8')
    result = compile_site(config)
    assert 'api/index.html' not in result.files
    assert 'API Docs</span>' not in result.files['index.html'].decode()
