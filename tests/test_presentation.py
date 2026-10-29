"""
title: Project menus, scoped APIs, authored layouts, and branding assets.
"""

from __future__ import annotations

import shutil

from pathlib import Path
from typing import cast

import pytest
import yaml

from doukimd.build import check_output_routes, compile_site
from doukimd.errors import BuildError
from doukimd.runtime import typechecked


@typechecked
def configure(project: Path, settings: dict[str, object]) -> Path:
    """
    title: Extend a fixture configuration with literal settings.
    parameters:
      project:
        type: Path
      settings:
        type: dict[str, object]
    returns:
      type: Path
    """
    path = project / 'doukimd.yaml'
    current = cast(dict[str, object], yaml.safe_load(path.read_text()))
    current.update(settings)
    path.write_text(yaml.safe_dump(current), encoding='utf-8')
    return path


@typechecked
def test_product_navigation_and_source_scope(example: Path) -> None:
    """
    title: Select product menus for authored and generated pages.
    parameters:
      example:
        type: Path
    """
    shutil.copytree(example / 'src', example / 'other-src')
    (example / 'docs/product').mkdir()
    (example / 'docs/product/index.md').write_text('# Overview\n\n## Start')
    (example / 'docs/index.md').write_text('# Home')
    config = configure(
        example,
        {
            'api': {
                'sources': [
                    {'name': 'first', 'root': 'src'},
                    {'name': 'second', 'root': 'other-src'},
                ]
            },
            'navigation': {
                'navbar': [
                    {'title': 'Product', 'path': 'product/index.md#start'},
                    {
                        'title': 'Tools',
                        'children': [
                            {
                                'title': 'Repository',
                                'url': 'https://example.com/repo',
                            },
                            {
                                'title': 'Contact',
                                'url': 'mailto:docs@example.com',
                            },
                        ],
                    },
                ],
                'default_sidebar': 'project',
                'sidebars': [
                    {
                        'id': 'project',
                        'title': 'Project',
                        'items': [
                            {'title': 'Home', 'path': 'index.md'},
                            {'title': 'All APIs', 'api': '*'},
                        ],
                    },
                    {
                        'id': 'product',
                        'title': 'Product',
                        'paths': ['product/', 'api/python/first/'],
                        'items': [
                            {
                                'title': 'Learn',
                                'children': [
                                    {
                                        'title': 'Introduction',
                                        'path': 'product/index.md',
                                    },
                                ],
                            },
                            {'title': 'Python API', 'api': 'first'},
                        ],
                    },
                ],
            },
        },
    )
    result = compile_site(config)
    html = result.files['api/python/first/example.add.html'].decode()
    sidebar = html.partition('<nav aria-label="Documentation">')[2]
    sidebar = sidebar.partition('</nav>')[0]
    assert 'Python API' in sidebar and 'Introduction' in sidebar
    assert 'second' not in sidebar and 'All APIs' not in sidebar
    assert 'href="example.add.html" aria-current="page"' in sidebar
    assert 'href="../../../product/index.html#start"' in html
    assert '<span class="nav-group"><span class="nav-label">Tools' in html
    assert 'href="https://example.com/repo"' in html
    home = result.files['index.html'].decode()
    assert 'All APIs' in home and 'first / example' in home
    assert 'second / example' in home
    # Explicit page choice overrides a matching product prefix.
    (example / 'docs/product/index.md').write_text(
        '---\nsidebar: project\n---\n# Overview\n\n## Start'
    )
    selected = compile_site(config).files['product/index.html'].decode()
    sidebar = selected.partition('<nav aria-label="Documentation">')[2]
    assert 'All APIs' in sidebar.partition('</nav>')[0]


@typechecked
def test_layout_branding_html_and_template_blocks(project: Path) -> None:
    """
    title: Render a landing page with local branding and reusable theme.
    parameters:
      project:
        type: Path
    """
    (project / 'docs/images').mkdir()
    (project / 'docs/images/logo.svg').write_text('<svg></svg>')
    (project / 'docs/favicon.ico').write_bytes(b'icon')
    (project / 'docs/styles.css').write_text('.hero { display: grid; }')
    (project / 'docs/nested').mkdir()
    (project / 'docs/nested/page.md').write_text(
        '# Guide\n\n[Hero](../index.md#hero)\n\n## Learn'
    )
    (project / 'docs/index.md').write_text(
        '---\nlayout: landing\nhtml: true\nrender: jinja\n'
        'template: home.html\n---\n'
        '<section id="hero" class="hero">\n\n'
        '# {{ project.name }}\n\n'
        '<img src="images/logo.svg" alt="Logo" />\n'
        '<a href="nested/page.md?view=all#learn">Start &amp; learn</a>\n'
        '<!-- retained -->&#169;\n\n</section>\n'
    )
    (project / 'theme').mkdir()
    (project / 'theme/home.html').write_text(
        '{% extends "page.html" %}{% block head %}'
        '<meta name="custom" content="yes">{% endblock %}'
        '{% block footer %}<footer>Custom footer</footer>{% endblock %}'
    )
    config = configure(
        project,
        {
            'site': {
                'title': 'Test',
                'description': 'A <compiler>',
                'logo': 'images/logo.svg',
                'logo_alt': 'Test logo',
                'favicon': 'favicon.ico',
            },
            'assets': ['images/**', 'favicon.ico', 'styles.css'],
            'theme': {'directory': 'theme', 'stylesheets': ['styles.css']},
        },
    )
    result = compile_site(config)
    html = result.files['index.html'].decode()
    assert 'page-layout-landing' in html
    assert '<nav aria-label="Documentation">' not in html
    assert 'aria-label="On this page"' not in html
    assert '<div class="page-heading">' not in html
    assert '<section id="hero" class="hero">' in html
    assert '<h1 id="test">test</h1>' in html
    assert 'href="nested/page.html?view=all#learn"' in html
    assert 'Start &amp; learn' in html and '<!-- retained -->' in html
    assert '<meta name="custom" content="yes">' in html
    assert 'A &lt;compiler&gt;' in html
    assert '<footer>Custom footer</footer>' in html
    nested = result.files['nested/page.html'].decode()
    assert 'href="../styles.css"' in nested
    assert 'href="../favicon.ico"' in nested
    assert 'src="../images/logo.svg" alt="Test logo"' in nested
    assert result.files['images/logo.svg'] == b'<svg></svg>'
    # HTML opt-in is page-local and cannot leak from earlier parses.
    (project / 'docs/nested/page.md').write_text(
        '---\nlayout: full\nsidebar: false\ntoc: false\nshow_title: false\n'
        '---\n# Guide\n\n## Learn\n\n<div>Escaped</div>\n'
    )
    plain = compile_site(config).files['nested/page.html'].decode()
    assert '&lt;div&gt;Escaped&lt;/div&gt;' in plain
    assert 'layout--no-sidebar layout--no-toc' in plain
    assert '<div class="page-heading">' not in plain


@typechecked
def test_authored_html_does_not_enable_docstring_html(example: Path) -> None:
    """
    title: Keep docstring HTML escaped even inside an HTML-enabled page.
    parameters:
      example:
        type: Path
    """
    source = example / 'src/example.py'
    source.write_text(
        source.read_text().replace('Example API', '<div>Example API</div>')
    )
    (example / 'docs/index.md').write_text(
        '---\nhtml: true\n---\n::: api example\n:::\n'
    )
    result = compile_site(example / 'doukimd.yaml')
    assert (
        '&lt;div&gt;Example API&lt;/div&gt;'
        in result.files['index.html'].decode()
    )


@pytest.mark.parametrize(
    ('settings', 'message'),
    [
        ({'navbar': [{'title': 'Bad', 'url': 'https://['}]}, 'Invalid URL'),
        ({'navbar': [{'title': 'Bad', 'path': 'https://['}]}, 'Invalid page'),
        ({'navbar': [{'title': 'Bad', 'path': 'missing.md'}]}, 'Unknown page'),
        (
            {'navbar': [{'title': 'Bad', 'path': 'index.md#missing'}]},
            'Unknown heading',
        ),
        (
            {'navbar': [{'title': 'Bad', 'path': '../index.md'}]},
            'Invalid page',
        ),
        (
            {'navbar': [{'title': 'Bad', 'url': 'javascript:alert(1)'}]},
            'Invalid URL',
        ),
        ({'navbar': [{'title': 'Bad', 'api': '*'}]}, 'not generated'),
        (
            {
                'navbar': [
                    {'title': 'Bad', 'path': 'index.md', 'url': 'https://a.b'}
                ]
            },
            'one of',
        ),
        ({'navbar': [{'title': 'Empty'}]}, 'one of'),
        (
            {
                'navbar': [
                    {
                        'title': 'Bad',
                        'api': '*',
                        'children': [{'title': 'Home', 'path': 'index.md'}],
                    }
                ]
            },
            'own children',
        ),
        ({'default_sidebar': 'missing'}, 'Unknown default sidebar'),
        (
            {
                'sidebars': [
                    {'id': 'same', 'title': 'One', 'items': []},
                    {'id': 'same', 'title': 'Two', 'items': []},
                ]
            },
            'Duplicate sidebar',
        ),
        (
            {
                'sidebars': [
                    {
                        'id': 'bad',
                        'title': 'Bad',
                        'paths': ['../'],
                        'items': [],
                    },
                ]
            },
            'route prefix',
        ),
        (
            {
                'sidebars': [
                    {
                        'id': 'one',
                        'title': 'One',
                        'paths': ['index.html'],
                        'items': [],
                    },
                    {
                        'id': 'two',
                        'title': 'Two',
                        'paths': ['index.html'],
                        'items': [],
                    },
                ]
            },
            'Ambiguous sidebar',
        ),
    ],
)
@typechecked
def test_invalid_navigation(
    project: Path, settings: dict[str, object], message: str
) -> None:
    """
    title: Fail at configuration or route resolution for unusable menus.
    parameters:
      project:
        type: Path
      settings:
        type: dict[str, object]
      message:
        type: str
    """
    config = configure(project, {'navigation': settings})
    with pytest.raises(BuildError, match=message):
        compile_site(config)


@pytest.mark.parametrize(
    ('text', 'message'),
    [
        ('---\nsidebar: missing\n---\n# Home', 'Unknown sidebar'),
        (
            '---\nhtml: true\n---\n<a href="missing.md">Bad</a>',
            'Unknown local target',
        ),
        (
            '---\nhtml: true\n---\n<a href="#missing">Bad</a>',
            'Unknown heading anchor',
        ),
        (
            '---\nhtml: true\n---\n<div id="same"></div>\n'
            '<span id="same"></span>',
            'Duplicate HTML id',
        ),
        (
            '---\ntemplate: ../escape.html\n---\n# Home',
            'relative project path',
        ),
        ('---\ntemplate: missing.html\n---\n# Home', 'missing.html'),
    ],
)
@typechecked
def test_invalid_presentation(project: Path, text: str, message: str) -> None:
    """
    title: Reject unknown menus, templates, HTML links, and duplicate anchors.
    parameters:
      project:
        type: Path
      text:
        type: str
      message:
        type: str
    """
    (project / 'docs/index.md').write_text(text)
    with pytest.raises(BuildError, match=message):
        compile_site(project / 'doukimd.yaml')


@pytest.mark.parametrize(
    ('settings', 'message'),
    [
        ({'assets': ['../outside/**']}, 'Invalid asset pattern'),
        ({'assets': ['missing.png']}, 'No assets match'),
        ({'assets': ['index.md']}, 'selects source'),
        ({'site': {'title': 'Test', 'logo': 'missing.svg'}}, 'not copied'),
        ({'theme': {'stylesheets': ['missing.css']}}, 'not copied'),
    ],
)
@typechecked
def test_invalid_branding(
    project: Path, settings: dict[str, object], message: str
) -> None:
    """
    title: Require branding assets to exist and be explicitly included.
    parameters:
      project:
        type: Path
      settings:
        type: dict[str, object]
      message:
        type: str
    """
    config = configure(project, settings)
    with pytest.raises(BuildError, match=message):
        compile_site(config)


@pytest.mark.parametrize(
    'name',
    [
        'theme.css',
        'THEME.CSS',
        'search.json',
        'symbols.json',
        '.doukimd-manifest.json',
        'index.html',
        'INDEX.HTML',
    ],
)
@typechecked
def test_asset_output_collisions(project: Path, name: str) -> None:
    """
    title: Reject assets that would overwrite theme, metadata, or page outputs.
    parameters:
      project:
        type: Path
      name:
        type: str
    """
    (project / 'docs' / name).write_text('collision')
    config = configure(project, {'assets': [name]})
    with pytest.raises(BuildError, match='collides'):
        compile_site(config)


@typechecked
def test_source_scope_and_longest_sidebar_prefix(example: Path) -> None:
    """
    title: Choose the most specific menu and reject unavailable source names.
    parameters:
      example:
        type: Path
    """
    (example / 'docs/index.md').write_text('# Home')
    settings: dict[str, object] = {
        'sidebars': [
            {
                'id': 'api',
                'title': 'API',
                'paths': ['api/'],
                'items': [{'title': 'General API', 'api': '*'}],
            },
            {
                'id': 'python',
                'title': 'Python',
                'paths': ['api/python/'],
                'items': [{'title': 'Specific API', 'api': '*'}],
            },
        ]
    }
    config = configure(example, {'navigation': settings})
    html = compile_site(config).files['api/python/example.html'].decode()
    sidebar = html.partition('<nav aria-label="Documentation">')[2]
    assert 'Specific API' in sidebar.partition('</nav>')[0]
    assert '<p class="sidebar-caption">Python</p>' in html
    config = configure(
        example,
        {'navigation': {'navbar': [{'title': 'Missing', 'api': 'missing'}]}},
    )
    with pytest.raises(BuildError, match='No API pages for source'):
        compile_site(config)


@typechecked
def test_file_directory_and_asset_case_collisions(project: Path) -> None:
    """
    title: Reject conflicts that would fail or lose files during publication.
    parameters:
      project:
        type: Path
    """
    with pytest.raises(BuildError, match='collides'):
        check_output_routes(['assets/logo.svg', 'assets/LOGO.svg'])
    config = configure(project, {'assets': ['index.html/**']})
    (project / 'docs/index.html').mkdir()
    (project / 'docs/index.html/child.txt').write_text('child')
    with pytest.raises(BuildError, match='collides'):
        compile_site(config)


@typechecked
def test_encoded_navigation_assets_and_html_anchors(project: Path) -> None:
    """
    title: Preserve URL semantics for filenames containing spaces and hashes.
    parameters:
      project:
        type: Path
    """
    (project / 'docs/assets').mkdir()
    (project / 'docs/assets/logo #1.svg').write_text('<svg></svg>')
    (project / 'docs/Guide #1.md').write_text(
        '---\nhtml: true\n---\n<span id="learn"></span>\n\n## Learn'
    )
    (project / 'docs/index.md').write_text(
        '---\nhtml: true\n---\n'
        '[Guide](Guide%20%231.md#learn)\n\n'
        '<a href="Guide%20%231%2Emd#learn-1">HTML link</a>\n'
    )
    config = configure(
        project,
        {
            'site': {'title': 'Test', 'logo': 'assets/logo #1.svg'},
            'navigation': {
                'navbar': [{'title': 'Guide', 'path': 'Guide%20%231.md#learn'}]
            },
        },
    )
    result = compile_site(config)
    html = result.files['index.html'].decode()
    assert 'href="Guide%20%231.html#learn"' in html
    assert 'href="Guide%20%231.html#learn-1"' in html
    assert 'src="assets/logo%20%231.svg"' in html
    assert '<h2 id="learn-1">' in result.files['Guide #1.html'].decode()
