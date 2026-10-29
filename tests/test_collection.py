"""
title: Public API fidelity and isolated monorepo source selection.
"""

from __future__ import annotations

import json

from pathlib import Path

import pytest

from doukimd.api import collect_api
from doukimd.build import compile_site
from doukimd.config import load_config
from doukimd.errors import BuildError
from doukimd.runtime import typechecked


@typechecked
def write_package(project: Path) -> None:
    """
    title: Create a static-only package with common public declaration kinds.
    parameters:
      project:
        type: Path
    """
    package = project / 'src/sample'
    package.mkdir(parents=True)
    (package / '__init__.py').write_text(
        '"""title: Public package."""\n'
        'from .model import Widget as PublicWidget, Color, Alias, VALUE\n'
        '__all__ = ["PublicWidget", "Color", "Alias", "VALUE"]\n',
        encoding='utf-8',
    )
    (package / 'model.py').write_text(
        '''
"""title: Model declarations."""
from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias
from plum import dispatch as specialize
VALUE: int = 3
Alias: TypeAlias = int | str
class Color(Enum):
    """title: Supported colors."""
    RED = "red"
    BLUE = "blue"
@dataclass
class Widget:
    """
    title: Widget declaration.
    attributes:
      value:
        type: int
        description: The stored value.
    """
    value: int = 1
    @property
    def doubled(self) -> int:
        """title: Double the value."""
        return self.value * 2
    @specialize
    def visit(self, value: int) -> int:
        """
        title: Handle integers.
        parameters:
          value: int
        """
        return value
    @specialize
    def visit(self, value: str) -> str:
        """
        title: Handle strings.
        parameters:
          value: str
        """
        return value
raise RuntimeError("Importing documentation sources is forbidden")
''',
        encoding='utf-8',
    )
    path = project / 'doukimd.yaml'
    path.write_text(
        path.read_text()
        + """api:
  sources:
    - name: models
      root: src
      modules: [sample]
""",
        encoding='utf-8',
    )


@typechecked
def test_public_declarations_and_variants(project: Path) -> None:
    """
    title: Render re-exports, generated constructors, fields, and dispatch.
    parameters:
      project:
        type: Path
    """
    write_package(project)
    config = load_config(project / 'doukimd.yaml')
    inventory = collect_api(project, config)
    widget = inventory['python:models:sample.PublicWidget']
    assert widget.canonical == 'python:models:sample.model.Widget'
    assert widget.source == 'src/sample/model.py'
    assert widget.signature.startswith('PublicWidget(')
    assert (
        inventory['python:models:sample.PublicWidget.value'].documentation[
            'summary'
        ]
        == 'The stored value.'
    )
    assert inventory['python:models:sample.PublicWidget.__init__'].generated
    assert (
        inventory['python:models:sample.PublicWidget.__init__'].line
        == widget.line
    )
    assert (
        inventory['python:models:sample.PublicWidget.doubled'].kind
        == 'property'
    )
    assert inventory['python:models:sample.Color.RED'].kind == 'enum-member'
    assert inventory['python:models:sample.Alias'].kind == 'type-alias'
    assert (
        inventory['python:models:sample.VALUE'].signature == 'VALUE: int = 3'
    )
    method = inventory['python:models:sample.PublicWidget.visit']
    assert len(method.variants) == 2
    assert 'int' in method.variants[0].signature
    assert 'str' in method.variants[1].signature
    assert method.variants[0].documentation['title'] == 'Handle integers.'
    (project / 'docs/index.md').write_text(
        """---
api_source: models
---
# Home
See {@api sample.PublicWidget.doubled}.
::: api sample.PublicWidget.visit
:::
""",
        encoding='utf-8',
    )
    site = compile_site(project / 'doukimd.yaml')
    html = site.files['index.html'].decode()
    assert 'Handle integers.' in html and 'Handle strings.' in html
    assert 'api/python/models/sample.PublicWidget.doubled.html' in html
    assert (
        b'Properties'
        in site.files['api/python/models/sample.PublicWidget.html']
    )
    assert b'Enum values' in site.files['api/python/models/sample.Color.html']


@typechecked
def test_folder_selection_and_ambiguous_references(project: Path) -> None:
    """
    title: Isolate identically named modules in two configured source roots.
    parameters:
      project:
        type: Path
    """
    for name, value in [('one', 1), ('two', 2)]:
        folder = project / name
        folder.mkdir()
        (folder / 'shared.py').write_text(
            f'"""title: Folder {name}."""\nVALUE = {value}\n'
            '__all__ = ["VALUE"]\n',
            encoding='utf-8',
        )
    path = project / 'doukimd.yaml'
    path.write_text(
        path.read_text()
        + """api:
  sources:
    - name: first
      root: one
      modules: [shared]
    - name: second
      root: two
      modules: [shared]
""",
        encoding='utf-8',
    )
    page = project / 'docs/index.md'
    page.write_text(
        """---
api_source: first
---
See {@api shared.VALUE} and {@api python:second:shared.VALUE}.
::: api shared.VALUE
source: second
:::
""",
        encoding='utf-8',
    )
    site = compile_site(path)
    html = site.files['index.html'].decode()
    assert 'api/python/first/shared.VALUE.html' in html
    assert 'api/python/second/shared.VALUE.html' in html
    assert '2' in html
    symbols = json.loads(site.files['symbols.json'])['symbols']
    assert symbols['python:first:shared.VALUE']['source_name'] == 'first'
    page.write_text('{@api shared.VALUE}', encoding='utf-8')
    with pytest.raises(BuildError, match='Ambiguous'):
        compile_site(path)
    page.write_text('---\napi_source: typo\n---\nHome', encoding='utf-8')
    with pytest.raises(BuildError, match='Unknown API source'):
        compile_site(path)
    page.write_text(
        '::: api shared.VALUE\nsource: typo\n:::', encoding='utf-8'
    )
    with pytest.raises(BuildError, match='Unknown API symbol'):
        compile_site(path)


@typechecked
def test_handwritten_missing_docs_still_fail(project: Path) -> None:
    """
    title: Require authored docstrings even for dataclass constructors.
    parameters:
      project:
        type: Path
    """
    write_package(project)
    source = project / 'src/sample/model.py'
    source.write_text(
        source.read_text().replace(
            '    value: int = 1',
            '    value: int = 1\n'
            '    def __init__(self) -> None:\n        pass',
        ),
        encoding='utf-8',
    )
    with pytest.raises(BuildError, match='Missing Douki docstring'):
        collect_api(project, load_config(project / 'doukimd.yaml'))


@typechecked
def test_non_dispatch_repetition_fails(project: Path) -> None:
    """
    title: Reject repeated definitions with no recognized overload semantics.
    parameters:
      project:
        type: Path
    """
    write_package(project)
    source = project / 'src/sample/model.py'
    source.write_text(
        source.read_text().replace('    @specialize\n', ''), encoding='utf-8'
    )
    with pytest.raises(BuildError, match='Unsupported repeated declaration'):
        collect_api(project, load_config(project / 'doukimd.yaml'))


@pytest.mark.parametrize('folder', ['src', 'src/sample'])
@typechecked
def test_source_folder_discovery(project: Path, folder: str) -> None:
    """
    title: Select either a source tree or a package folder without modules.
    parameters:
      project:
        type: Path
      folder:
        type: str
    """
    write_package(project)
    config = project / 'doukimd.yaml'
    config.write_text(
        config.read_text()
        .replace('root: src', f'root: {folder}')
        .replace('      modules: [sample]\n', ''),
        encoding='utf-8',
    )
    assert 'python:models:sample.PublicWidget' in collect_api(
        project, load_config(config)
    )


@typechecked
def test_case_insensitive_export_routes(project: Path) -> None:
    """
    title: Keep public classes and similarly named modules on distinct routes.
    parameters:
      project:
        type: Path
    """
    write_package(project)
    source = project / 'src/sample/__init__.py'
    source.write_text(
        source.read_text()
        .replace(
            'from .model import Widget as PublicWidget, Color, Alias, VALUE',
            'from .model import Widget as PublicWidget, '
            'Widget as Model, Color, Alias, VALUE',
        )
        .replace('"PublicWidget",', '"PublicWidget", "Model",'),
        encoding='utf-8',
    )
    (project / 'docs/index.md').write_text(
        """---
api_source: models
---
See {@api sample.Model} and {@api sample.model}.
""",
        encoding='utf-8',
    )
    site = compile_site(project / 'doukimd.yaml')
    symbols = json.loads(site.files['symbols.json'])['symbols']
    first = symbols['python:models:sample.Model']['url']
    second = symbols['python:models:sample.model']['url']
    assert first.casefold() != second.casefold()
    assert first in site.files and second in site.files
    assert first.encode() in site.files['index.html']
    assert second.encode() in site.files['index.html']


@pytest.mark.parametrize(
    'variant', ['registration', 'local', 'typing', 'private']
)
@typechecked
def test_variant_forms(project: Path, variant: str) -> None:
    """
    title: Preserve imported registrations, local dispatch, and overloads.
    parameters:
      project:
        type: Path
      variant:
        type: str
    """
    write_package(project)
    source = project / 'src/sample/model.py'
    text = source.read_text()
    if variant == 'registration':
        (source.parent / 'base.py').write_text(
            '''
"""title: Dispatcher base."""
from plum import dispatch
class Base:
    """title: Base visitor."""
    @dispatch
    def visit(self, value: object) -> object:
        """title: Handle objects."""
        return value
''',
            encoding='utf-8',
        )
        text = 'from .base import Base\n' + text
        # Keep the module docstring first.
        text = text.replace('from .base import Base\n', '').replace(
            'from dataclasses import dataclass',
            'from .base import Base\nfrom dataclasses import dataclass',
        )
        text = text.replace('@specialize', '@Base.visit.dispatch')
    elif variant == 'local':
        last = text.rfind('@specialize')
        text = text[:last] + text[last:].replace(
            '@specialize', '@visit.dispatch', 1
        )
    elif variant == 'typing':
        text = text.replace(
            'from plum import dispatch as specialize',
            'from typing import overload as specialize',
        )
        text = text.replace(
            'raise RuntimeError(',
            '''    def visit(self, value: object) -> object:
        """title: Implementation."""
        return value
raise RuntimeError(''',
        )
    else:
        text = text.replace(
            'from dataclasses import dataclass',
            'from public import private\nfrom dataclasses import dataclass',
        )
        last = text.rfind('@specialize')
        text = text[:last] + text[last:].replace(
            '@specialize', '@private\n    @specialize', 1
        )
    source.write_text(text, encoding='utf-8')
    inventory = collect_api(project, load_config(project / 'doukimd.yaml'))
    item = inventory['python:models:sample.PublicWidget.visit']
    assert len(item.variants) == (1 if variant == 'private' else 2)
    assert 'int' in item.variants[0].signature


@pytest.mark.parametrize(
    'case',
    [
        'duplicate',
        'empty',
        'missing',
        'module-doc',
        'cycle',
        'escape',
        'namespace',
    ],
)
@typechecked
def test_source_errors(project: Path, case: str) -> None:
    """
    title: Fail closed on invalid source selection and invalid exports.
    parameters:
      project:
        type: Path
      case:
        type: str
    """
    write_package(project)
    path = project / 'doukimd.yaml'
    if case == 'duplicate':
        path.write_text(
            path.read_text() + '    - name: models\n      root: src\n',
            encoding='utf-8',
        )
    elif case in {'empty', 'missing'}:
        if case == 'empty':
            (project / 'empty').mkdir()
        path.write_text(
            path.read_text()
            .replace('root: src', f'root: {case}')
            .replace('      modules: [sample]\n', ''),
            encoding='utf-8',
        )
    elif case == 'namespace':
        (project / 'src/namespace').mkdir()
        (project / 'src/namespace/sub.py').write_text(
            '"""title: Namespace."""', encoding='utf-8'
        )
        path.write_text(
            path.read_text().replace('      modules: [sample]\n', ''),
            encoding='utf-8',
        )
    elif case == 'module-doc':
        source = project / 'src/sample/__init__.py'
        source.write_text(
            source.read_text().replace('"""title: Public package."""', ''),
            encoding='utf-8',
        )
    elif case == 'cycle':
        (project / 'src/sample/__init__.py').write_text(
            '''
"""title: Cycle."""
from .cycle import VALUE
__all__ = ["VALUE"]
''',
            encoding='utf-8',
        )
        (project / 'src/sample/cycle.py').write_text(
            '''
"""title: Cycle."""
from sample import VALUE
__all__ = ["VALUE"]
''',
            encoding='utf-8',
        )
    else:
        external = project / 'docs/foreign.py'
        external.write_text(
            '"""title: Outside selected source."""\n', encoding='utf-8'
        )
        try:
            (project / 'src/sample/foreign.py').symlink_to(external)
        except OSError:
            pytest.skip('Symlink creation unavailable')
    with pytest.raises(BuildError):
        collect_api(project, load_config(path))
