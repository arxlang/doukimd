"""
title: Generated API entry points, hierarchy, and navigation behavior.
"""

from __future__ import annotations

import re

from dataclasses import replace
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pytest

from doukimd.api import collect_api
from doukimd.build import compile_site
from doukimd.config import load_config
from doukimd.content import discover_pages, plan_pages
from doukimd.errors import BuildError
from doukimd.indexes import ApiIndex, SiteIndex
from doukimd.models import (
    ApiSymbol,
    Config,
    NavigationItem,
    Page,
    PageSettings,
)
from doukimd.navigation import build_navbar, build_navigation
from doukimd.navigation_plan import NavigationPlan, NavigationView
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
    title: Keep titles distinct inside a stable module accordion.
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
    assert api.layout == 'modules'
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
    assert 'class="sidebar-group"' not in nav
    assert len(re.findall(r'<details class="api-module"[^>]* open>', nav)) == 1
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


@typechecked
def test_flat_api_navigation_reaches_all_nested_pages(example: Path) -> None:
    """
    title: Keep module order stable and reach members through class pages.
    parameters:
      example:
        type: Path
    """
    package = example / 'src/package'
    package.mkdir()
    (package / '__init__.py').write_text('"""title: Package."""')
    (package / 'nested.py').write_text(
        '"""title: Nested module."""\n'
        'class Widget:\n'
        '    """title: Widget."""\n'
        '    class Inner:\n'
        '        """title: Nested class."""\n'
        '        def create(self) -> None:\n'
        '            """title: Create an item."""\n'
    )
    config = example / 'doukimd.yaml'
    config.write_text(
        config.read_text().replace('[example]', '[example, package]')
    )
    result = compile_site(config)
    routes = {
        route
        for route in result.files
        if route.startswith('api/') and route.endswith('.html')
    }
    pending = ['api/index.html']
    visited: set[str] = set()
    while pending:
        route = pending.pop()
        if route in visited:
            continue
        visited.add(route)
        html = result.files[route].decode()
        sidebar = html.partition('<nav aria-label="Documentation">')[2]
        sidebar = sidebar.partition('</nav>')[0]
        assert 'class="sidebar-group"' not in sidebar
        assert sidebar.count('aria-current=') == 1
        modules = re.findall(
            r'<details class="api-module" name="[^"]+"([^>]*)>\s*'
            r'<summary><span class="nav-label">(.*?)</span></summary>',
            sidebar,
        )
        assert [title for _, title in modules] == [
            'example',
            'package',
            'package.nested',
        ]
        opened = [
            title for attributes, title in modules if 'open' in attributes
        ]
        assert len(opened) == 1
        if route.startswith('api/python/package.nested'):
            assert opened == ['package.nested']
        for section in re.findall(
            r'<details class="api-module"[^>]*>(.*?)</details>',
            sidebar,
            re.DOTALL,
        ):
            assert '<details' not in section
        main = html.partition('<main id="content">')[2].partition('</main>')[0]
        for href in re.findall(r'href="([^"]+)"', sidebar + main):
            target = urlsplit(urljoin(f'https://docs.example/{route}', href))
            path = target.path.lstrip('/')
            if path.endswith('/'):
                path += 'index.html'
            if path in routes:
                pending.append(path)
    assert visited == routes
    assert 'api/python/package.nested.Widget.Inner.create.html' in visited


@typechecked
def test_empty_api_owner_retains_location(example: Path) -> None:
    """
    title: Keep an empty module's overview accessible inside its accordion.
    parameters:
      example:
        type: Path
    """
    (example / 'src/empty.py').write_text('"""title: Empty module."""')
    (example / 'docs/index.md').write_text('# Home')
    config = example / 'doukimd.yaml'
    config.write_text(config.read_text().replace('[example]', '[empty]'))
    html = compile_site(config).files['api/python/empty.html'].decode()
    sidebar = html.partition('<nav aria-label="Documentation">')[2]
    sidebar = sidebar.partition('</nav>')[0]
    assert (
        'href="empty.html" aria-label="empty module overview"'
        ' aria-current="page">Module overview</a>' in sidebar
    )
    assert (
        len(re.findall(r'<details class="api-module"[^>]* open>', sidebar))
        == 1
    )
    assert 'href="../"' in sidebar


@pytest.mark.parametrize('symbol', ['python:example', 'python:example.add'])
@typechecked
def test_unknown_api_navigation_kind_fails(example: Path, symbol: str) -> None:
    """
    title: Reject an unsupported declaration kind instead of losing its link.
    parameters:
      example:
        type: Path
      symbol:
        type: str
    """
    config = load_config(example / 'doukimd.yaml')
    inventory = collect_api(example, config)
    pages = discover_pages(example, config)
    plan_pages(pages, inventory, config)
    current = next(page for page in pages if page.symbol == 'python:example')
    inventory[symbol] = replace(inventory[symbol], kind='unsupported')
    with pytest.raises(BuildError, match=r'Unsupported API .*kind'):
        build_navigation(pages, current, inventory)


@typechecked
def test_selected_nested_roots_have_distinct_module_names(
    example: Path,
) -> None:
    """
    title: Distinguish same-named nested modules selected as separate roots.
    parameters:
      example:
        type: Path
    """
    for name in ['first', 'second']:
        package = example / 'src' / name
        package.mkdir()
        (package / '__init__.py').write_text('"""title: Package."""')
        (package / 'nested.py').write_text('"""title: Nested module."""')
    (example / 'docs/index.md').write_text('# Home')
    config = example / 'doukimd.yaml'
    config.write_text(
        config.read_text().replace(
            '[example]', '[first.nested, second.nested]'
        )
    )
    result = compile_site(config)
    for name in ['first', 'second']:
        html = result.files[f'api/python/{name}.nested.html'].decode()
        sidebar = html.partition('<nav aria-label="Documentation">')[2]
        sidebar = sidebar.partition('</nav>')[0]
        groups = re.findall(
            r'<details class="api-module" name="[^"]+"([^>]*)>\s*'
            r'<summary><span class="nav-label">(.*?)</span></summary>',
            sidebar,
        )
        assert [title for _, title in groups] == [
            'first.nested',
            'second.nested',
        ]
        assert [title for attrs, title in groups if 'open' in attrs] == [
            f'{name}.nested'
        ]


@typechecked
def navigation_data(
    items: list[NavigationItem] | tuple[NavigationView, ...],
) -> list[dict[str, object]]:
    """
    title: Compare every documented theme field across both navigation paths.
    parameters:
      items:
        type: list[NavigationItem] | tuple[NavigationView, Ellipsis]
    returns:
      type: list[dict[str, object]]
    """
    return [
        {
            'title': item.title,
            'url': item.url,
            'kind': item.kind,
            'layout': item.layout,
            'current': item.current,
            'active': item.active,
            'children': navigation_data(item.children),
        }
        for item in items
    ]


@pytest.mark.parametrize('configured', [False, True])
@typechecked
def test_prepared_navigation_matches_standalone_helpers(
    configured: bool,
) -> None:
    """
    title: Preserve links and flags across directories and source scopes.
    parameters:
      configured:
        type: bool
    """
    names = [
        ('one', 'one', 'module', None),
        ('one', 'one.child', 'module', 'one'),
        ('one', 'one.child.Widget', 'class', 'one.child'),
        ('one', 'one.child.Widget.Inner', 'class', 'one.child.Widget'),
        (
            'one',
            'one.child.Widget.Inner.method',
            'method',
            'one.child.Widget.Inner',
        ),
        ('two', 'two', 'module', None),
        ('two', 'two.value', 'attribute', 'two'),
    ]
    inventory = {
        f'python:{source}:{name}': ApiSymbol(
            identifier=f'python:{source}:{name}',
            name=name.rsplit('.', 1)[-1],
            kind=kind,
            signature='',
            source='src/example.py',
            line=1,
            documentation={'title': name},
            parent=f'python:{source}:{parent}' if parent else None,
            source_name=source,
        )
        for source, name, kind, parent in names
    }
    pages = [
        Page('index.html', 'Home', '', PageSettings()),
        Page('guide/index.html', 'Guide', '', PageSettings()),
        Page('guide/é space/index.html', 'Unicode', '', PageSettings()),
        Page('guide/é space/file #?.html', 'Escaped', '', PageSettings()),
        Page(
            'guide/custom.html',
            'Custom',
            '',
            PageSettings(sidebar='all') if configured else PageSettings(),
        ),
        Page('hidden.html', 'Hidden', '', PageSettings(sidebar=False)),
        Page('landing.html', 'Landing', '', PageSettings(layout='landing')),
    ]
    pages[1].anchors.add('section')
    config = Config(
        site={'title': 'Docs'},
        project={'name': 'test'},
        navigation={
            'navbar': [
                {'title': 'Home', 'path': 'index.md'},
                {'title': 'One', 'api': 'one'},
                {'title': 'All APIs', 'api': '*'},
                {
                    'title': 'Guide',
                    'path': 'guide/index.md',
                    'children': [
                        {
                            'title': 'Unicode',
                            'path': 'guide/é%20space/index.md',
                        },
                        {
                            'title': 'Escaped',
                            'path': 'guide/é%20space/file%20%23%3F.md',
                        },
                    ],
                },
            ],
            **(
                {
                    'default_sidebar': 'all',
                    'sidebars': [
                        {
                            'id': 'all',
                            'title': 'All docs',
                            'items': [
                                {
                                    'title': 'Guide',
                                    'path': 'guide/index.md?view=one#section',
                                },
                                {'title': 'API', 'api': '*'},
                            ],
                        },
                        {
                            'id': 'one',
                            'title': 'One docs',
                            'paths': ['guide/', 'api/python/one/'],
                            'items': [
                                {
                                    'title': 'Learn',
                                    'children': [
                                        {
                                            'title': 'Guide',
                                            'path': 'guide/index.md',
                                        },
                                        {
                                            'title': 'Unicode',
                                            'path': 'guide/é%20space/index.md',
                                        },
                                        {
                                            'title': 'External',
                                            'url': 'https://example.org/',
                                        },
                                    ],
                                },
                                {'title': 'One API', 'api': 'one'},
                            ],
                        },
                    ],
                }
                if configured
                else {}
            ),
        },
    )
    routes = plan_pages(pages, inventory, config)
    api = ApiIndex(inventory, routes)
    plan = NavigationPlan(SiteIndex(pages), api, config)
    snapshots = []
    for page in pages:
        sidebar = plan.navigation(page)
        header = plan.header(page)
        expected = build_navigation(pages, page, inventory, config)
        assert navigation_data(sidebar) == navigation_data(expected)
        assert navigation_data(header) == navigation_data(
            build_navbar(config, pages, page, inventory)
        )
        snapshots.append(navigation_data(sidebar))
    # Reusing the plan cannot change previously returned page selections.
    assert navigation_data(plan.navigation(pages[0])) == snapshots[0]
    if snapshots[0]:
        assert isinstance(plan.navigation(pages[0])[0].children, tuple)


@typechecked
def test_menu_preparation_is_scoped_to_each_build(
    example: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    title: Prepare navigation once per build and refresh after source changes.
    parameters:
      example:
        type: Path
      monkeypatch:
        type: pytest.MonkeyPatch
    """
    import doukimd.navigation_plan as planning

    original = planning.automatic_navigation
    calls = 0

    @typechecked
    def counted(
        pages: SiteIndex | list[Page],
        current: Page,
        inventory: ApiIndex | dict[str, ApiSymbol],
    ) -> list[NavigationItem]:
        """
        title: Count full hierarchy preparation independently of page count.
        parameters:
          pages:
            type: SiteIndex | list[Page]
          current:
            type: Page
          inventory:
            type: ApiIndex | dict[str, ApiSymbol]
        returns:
          type: list[NavigationItem]
        """
        nonlocal calls
        calls += 1
        return original(pages, current, inventory)

    monkeypatch.setattr(planning, 'automatic_navigation', counted)
    source = example / 'src/example.py'
    source.write_text(
        source.read_text()
        + '\n'.join(
            f'\ndef item_{number}() -> None:\n'
            f'    """title: Item {number}."""\n'
            for number in range(32)
        )
    )
    first = compile_site(example / 'doukimd.yaml')
    assert first.page_count > 32
    assert calls == 1
    source.write_text(
        source.read_text()
        + '\ndef later() -> None:\n    """title: Later."""\n'
    )
    second = compile_site(example / 'doukimd.yaml')
    assert calls == 2
    assert 'api/python/example.later.html' not in first.files
    assert 'api/python/example.later.html' in second.files
