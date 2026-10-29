"""
title: Framework selection, local assets, and semantic API labels.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess

from pathlib import Path

import pytest

from doukimd.api import collect_api
from doukimd.build import compile_site
from doukimd.config import load_config
from doukimd.errors import BuildError
from doukimd.models import ThemeSettings
from doukimd.runtime import typechecked


@typechecked
def test_bundled_bootstrap_is_default_and_offline(example: Path) -> None:
    """
    title: Ship pinned local CSS with its license and nested-page URLs.
    parameters:
      example:
        type: Path
    """
    assert ThemeSettings().framework == 'bootstrap'
    result = compile_site(example / 'doukimd.yaml')
    css = result.files['_doukimd/bootstrap/bootstrap.min.css']
    integrity = base64.b64encode(hashlib.sha384(css).digest()).decode()
    assert integrity == (
        'sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB'
    )
    assert b'MIT License' in result.files['_doukimd/bootstrap/LICENSE']
    html = result.files['api/python/example.add.html'].decode()
    assert 'href="../../_doukimd/bootstrap/bootstrap.min.css"' in html
    assert 'src="../../theme.js"' in html
    assert 'https://' not in html
    assert html.count('<h1') == 1
    assert '<pre class="highlight"><code>' in html
    assert '<code class="language-python"><div' not in html
    assert 'api-kind--function">function</span>' in html
    assert 'data-color-mode="auto"' in html
    assert b'[data-bs-theme="light"] .highlight' in result.files['theme.css']
    assert b'[data-bs-theme="dark"] .highlight' in result.files['theme.css']


@pytest.mark.parametrize('mode', ['light', 'dark', 'auto'])
@typechecked
def test_framework_none_and_color_defaults(project: Path, mode: str) -> None:
    """
    title: Preserve the bundled layout and controls without Bootstrap.
    parameters:
      project:
        type: Path
      mode:
        type: str
    """
    path = project / 'doukimd.yaml'
    path.write_text(
        path.read_text()
        + f'theme:\n  framework: none\n  color_mode: {mode}\n',
        encoding='utf-8',
    )
    result = compile_site(path)
    html = result.files['index.html'].decode()
    assert '_doukimd/bootstrap/bootstrap.min.css' not in result.files
    assert 'bootstrap.min.css' not in html
    assert 'Color mode' in html
    assert f'data-color-mode="{mode}"' in html
    expected = 'light' if mode == 'auto' else mode
    assert f'data-bs-theme="{expected}"' in html


@pytest.mark.parametrize(
    'setting',
    [
        'framework: unknown',
        'framework: false',
        'color_mode: blue',
        'color_mode: 1',
    ],
)
@typechecked
def test_unknown_theme_options_fail(project: Path, setting: str) -> None:
    """
    title: Reject unsupported frontend frameworks and invalid color modes.
    parameters:
      project:
        type: Path
      setting:
        type: str
    """
    path = project / 'doukimd.yaml'
    path.write_text(
        path.read_text() + f'theme:\n  {setting}\n', encoding='utf-8'
    )
    with pytest.raises(BuildError, match='config'):
        compile_site(path)


@typechecked
def test_class_methods_have_distinct_labels(example: Path) -> None:
    """
    title: Classify methods by their actual parent and retain summary links.
    parameters:
      example:
        type: Path
    """
    source = example / 'src/example.py'
    source.write_text(
        source.read_text() + '\nclass Widget:\n'
        '    """title: Widget."""\n'
        '    @staticmethod\n'
        '    def create() -> None:\n'
        '        """title: Create a widget."""\n',
        encoding='utf-8',
    )
    inventory = collect_api(example, load_config(example / 'doukimd.yaml'))
    assert inventory['python:example.Widget.create'].kind == 'method'
    result = compile_site(example / 'doukimd.yaml')
    html = result.files['api/python/example.Widget.create.html'].decode()
    assert 'api-kind--method">method</span>' in html
    assert 'api-kind--class">class</span>' in html
    assert 'api-kind--module">module</span>' in html
    assert (
        '<h2 id="methods">Methods</h2>'
        in result.files['api/python/example.Widget.html'].decode()
    )
    symbols = json.loads(result.files['symbols.json'])['symbols']
    assert symbols['python:example.Widget.create']['kind'] == 'method'


@typechecked
def test_frontend_preferences() -> None:
    """
    title: Exercise the shipped JavaScript with browser event contracts.
    """
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node is required only for frontend regression checks')
    directory = Path(__file__).parent
    subprocess.run(
        [
            node,
            str(directory / 'theme.cjs'),
            str(directory.parent / 'src/doukimd/themes/default/theme.js'),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
