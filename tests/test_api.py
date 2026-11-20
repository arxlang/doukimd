"""
title: Static Python collection and Douki rendering boundaries.
"""

from __future__ import annotations

import json

from pathlib import Path

import griffe
import pytest

from doukimd.api import (
    annotation_signature,
    collect_api,
    signature,
    source_path,
    visit,
)
from doukimd.build import compile_site
from doukimd.config import load_config
from doukimd.errors import BuildError
from doukimd.runtime import typechecked


@typechecked
def test_collection_never_imports_code(example: Path) -> None:
    """
    title: Extract API data even when importing the module would fail.
    parameters:
      example:
        description: Copy of the complete example project.
    """
    source = example / 'src/example.py'
    source.write_text(
        source.read_text() + '\nraise RuntimeError("do not import")\n',
        encoding='utf-8',
    )
    inventory = collect_api(example, load_config(example / 'doukimd.yaml'))
    assert 'python:example.add' in inventory
    assert 'python:example.helper' not in inventory


@typechecked
def test_description_only_docstrings(example: Path) -> None:
    """
    title: Collect Douki 0.14 prose and render source types without rewrites.
    parameters:
      example: Copy of the complete example project.
    """
    source = example / 'src/example.py'
    source.write_text(
        source.read_text()
        .replace(
            'left:\n        description: First value.', 'left: First value.'
        )
        .replace('returns:\n      description: The sum.', 'returns: The sum.'),
        encoding='utf-8',
    )
    original = source.read_bytes()
    inventory = collect_api(example, load_config(example / 'doukimd.yaml'))
    item = inventory['python:example.add']
    assert item.signature == 'add(left: int, right: int = 0) -> int'
    assert item.documentation['parameters'] == {
        'left': {'description': 'First value.', 'type': 'int'},
        'right': {'description': 'Second value.', 'default': 0, 'type': 'int'},
    }
    assert item.documentation['returns'] == {
        'description': 'The sum.',
        'type': 'int',
    }
    result = compile_site(example / 'doukimd.yaml')
    html = result.files['api/python/example.add.html'].decode()
    assert 'First value.' in html
    assert 'Second value.' in html
    assert 'The sum.' in html
    symbols = json.loads(result.files['symbols.json'])['symbols']
    assert symbols[item.identifier]['signature'] == item.signature
    assert source.read_bytes() == original


@typechecked
def test_static_parameter_kinds(example: Path) -> None:
    """
    title: Enrich variadic parameters from static annotations alone.
    parameters:
      example: Copy of the complete example project.
    """
    source = example / 'src/example.py'
    source.write_text(
        source.read_text() + '\ndef variadic(first: int, /, *values: str, '
        'flag: bool = True, **options: float) -> list[str]:\n'
        '    """title: Collect values."""\n'
        '    raise RuntimeError("never execute")\n',
        encoding='utf-8',
    )
    inventory = collect_api(example, load_config(example / 'doukimd.yaml'))
    data = inventory['python:example.variadic'].documentation
    assert data['parameters'] == {
        'first': {'type': 'int'},
        'values': {'type': 'str', 'variadic': 'positional'},
        'flag': {'type': 'bool'},
        'options': {'type': 'float', 'variadic': 'keyword'},
    }
    assert data['returns'] == {'type': 'list[str]'}


@pytest.mark.parametrize(
    ('original', 'replacement', 'message'),
    [
        ('left: int', 'left', "parameter 'left'"),
        ('-> int:', ':', 'return value'),
        (
            'from public import private, public',
            'from public import private, public\n'
            'class Missing:\n'
            '    """\n    title: Missing annotation.\n'
            '    attributes:\n      value: Stored value.\n    """\n'
            '    value = 1\n',
            "attribute 'value'",
        ),
    ],
)
@typechecked
def test_missing_annotations(
    example: Path, original: str, replacement: str, message: str
) -> None:
    """
    title: Report annotation failures at the static collection boundary.
    parameters:
      example: Copy of the complete example project.
      original: Source fragment containing the annotated declaration.
      replacement: Source fragment omitting a required annotation.
      message: Annotation diagnostic expected from Douki.
    """
    source = example / 'src/example.py'
    source.write_text(
        source.read_text().replace(original, replacement), encoding='utf-8'
    )
    with pytest.raises(BuildError, match=message) as caught:
        collect_api(example, load_config(example / 'doukimd.yaml'))
    assert caught.value.phase == 'douki'
    assert 'annotations' in str(caught.value)


@pytest.mark.parametrize(
    ('replacement', 'message'),
    [
        ('title: Add two integers.', 'Missing'),
        ('title: Add two integers.\n    unknown: true', 'schema'),
        (
            'title: Add two integers.\n    parameters:\n'
            '      left: {type: int}\n      right: Second value.',
            'schema',
        ),
        (
            'title: Add two integers.\n    returns: {type: int}',
            'schema',
        ),
        (
            'title: Add two integers.\n    attributes:\n'
            '      value: {type: int}',
            'schema',
        ),
        (
            'title: Add two integers.\n    warnings:\n'
            '      - type: UserWarning\n        description: Old format.',
            'schema',
        ),
        (
            'title: Add two integers.\n    parameters:\n'
            '      wrong: An unknown parameter.',
            'match',
        ),
    ],
)
@typechecked
def test_invalid_douki(example: Path, replacement: str, message: str) -> None:
    """
    title: Reject missing docstrings and invalid schema or parameter names.
    parameters:
      example:
        description: Copy of the complete example project.
      replacement:
        description: Replacement source content used to exercise validation.
      message:
        description: Diagnostic expected or reported for the failure.
    """
    source = example / 'src/example.py'
    text = source.read_text()
    if message == 'Missing':
        start = text.index('    """', text.index('def add'))
        end = text.index('    """', start + 7) + 7
        text = text[:start] + text[end:]
    else:
        start = text.index('    """', text.index('def add'))
        end = text.index('    """', start + 7) + 7
        text = (
            text[:start] + f'    """\n    {replacement}\n    """' + text[end:]
        )
    source.write_text(text, encoding='utf-8')
    with pytest.raises(BuildError, match=message):
        compile_site(example / 'doukimd.yaml')


@typechecked
def test_explicit_visibility_and_class_members(example: Path) -> None:
    """
    title: Respect aliases of atpublic decorators and retain underscore names.
    parameters:
      example:
        description: Copy of the complete example project.
    """
    source = example / 'src/example.py'
    source.write_text(
        source.read_text() + '\nfrom public import private as internal\n'
        '\n@internal\ndef not_public() -> None:\n'
        '    """title: Hidden by decorator alias."""\n'
        '\ndef _visible() -> None:\n'
        '    """title: Public without an explicit privacy marker."""\n'
        '\nclass Counter:\n'
        '    """title: A counter."""\n'
        '    def increment(self, amount: int = 1) -> int:\n'
        '        """\n'
        '        title: Increment the counter.\n'
        '        parameters:\n'
        '          amount: Increase applied to the counter.\n'
        '        """\n'
        '        return amount\n'
        '\nclass Hidden:\n'
        '    """\n'
        '    title: Hidden class.\n'
        '    visibility: private\n'
        '    """\n',
        encoding='utf-8',
    )
    (example / 'docs/index.md').write_text(
        '::: api python:example.Counter\nmembers: public\n:::\n',
        encoding='utf-8',
    )
    result = compile_site(example / 'doukimd.yaml')
    html = result.files['index.html'].decode()
    assert 'increment' in html
    assert 'amount' in html
    inventory = json.loads(result.files['symbols.json'])['symbols']
    assert 'python:example._visible' in inventory
    assert 'python:example.Counter.increment' in inventory
    assert 'python:example.not_public' not in inventory
    assert 'python:example.Hidden' not in inventory


@typechecked
def test_docstrings_are_never_templates(example: Path) -> None:
    """
    title: Preserve Jinja-looking prose and arbitrary valid Douki fields.
    parameters:
      example:
        description: Copy of the complete example project.
    """
    source = example / 'src/example.py'
    source.write_text(
        source.read_text().replace(
            'summary: Return the sum of the arguments.',
            'summary: "{{ missing_variable }}"\n'
            '    notes: A useful note.\n'
            '    raises:\n'
            '      ValueError: An example exception.\n'
            '    references: [Reference one, Reference two]\n'
            '    warnings:\n'
            '      UserWarning: Example warning.\n'
            '    deprecated: Use a newer function.\n',
        ),
        encoding='utf-8',
    )
    result = compile_site(example / 'doukimd.yaml')
    html = result.files['api/python/example.add.html'].decode()
    assert '{{ missing_variable }}' in html
    assert 'A useful note.' in html
    assert 'Reference two' in html
    assert 'Example warning' in html


@typechecked
def test_docstrings_cannot_expand_api_blocks(example: Path) -> None:
    """
    title: Prevent recursive API expansion through documentation prose.
    parameters:
      example:
        description: Copy of the complete example project.
    """
    source = example / 'src/example.py'
    source.write_text(
        source.read_text().replace(
            'summary: Return the sum of the arguments.',
            'summary: |\n      ::: api python:example.add\n      :::',
        ),
        encoding='utf-8',
    )
    with pytest.raises(BuildError, match='inside docstrings'):
        compile_site(example / 'doukimd.yaml')


@pytest.mark.parametrize(
    ('source', 'message'),
    [
        ('__all__ = ["add"]\n', None),
        ('from other import item\n__all__ = ["item"]\n', 're-export'),
    ],
)
@typechecked
def test_explicit_exports(
    example: Path, source: str, message: str | None
) -> None:
    """
    title: Honor declared exports and reject unsupported exported objects.
    parameters:
      example:
        description: Copy of the complete example project.
      source:
        description: Source content or configured API source name.
      message:
        description: Diagnostic expected or reported for the failure.
    """
    path = example / 'src/example.py'
    path.write_text(path.read_text() + '\n' + source, encoding='utf-8')
    if message is None:
        inventory = collect_api(example, load_config(example / 'doukimd.yaml'))
        assert set(inventory) == {'python:example', 'python:example.add'}
    else:
        with pytest.raises(BuildError, match=message):
            compile_site(example / 'doukimd.yaml')


@pytest.mark.parametrize(
    'module', ['missing', '../example', 'example/example']
)
@typechecked
def test_bad_modules(example: Path, module: str) -> None:
    """
    title: Report invalid module identifiers and missing source.
    parameters:
      example:
        description: Copy of the complete example project.
      module:
        description: Python import path selected for collection.
    """
    path = example / 'doukimd.yaml'
    path.write_text(
        path.read_text().replace(
            'modules: [example]', f'modules: ["{module}"]'
        ),
        encoding='utf-8',
    )
    with pytest.raises(BuildError, match='api'):
        compile_site(path)


@typechecked
def test_duplicate_sources_and_routes(example: Path) -> None:
    """
    title: Reject duplicate symbols and authored route collisions.
    parameters:
      example:
        description: Copy of the complete example project.
    """
    path = example / 'doukimd.yaml'
    original = path.read_text()
    path.write_text(
        original + '    - root: src\n      modules: [example]\n',
        encoding='utf-8',
    )
    with pytest.raises(BuildError, match='Duplicate API symbol'):
        compile_site(path)
    path.write_text(original, encoding='utf-8')
    route = example / 'docs/api/python'
    route.mkdir(parents=True)
    (route / 'example.add.md').write_text('# Collision', encoding='utf-8')
    with pytest.raises(BuildError, match='Duplicate route'):
        compile_site(path)


@typechecked
def test_disabling_generated_pages(example: Path) -> None:
    """
    title: Support embedded API documentation without virtual pages.
    parameters:
      example:
        description: Copy of the complete example project.
    """
    path = example / 'doukimd.yaml'
    path.write_text(
        path.read_text().replace('api:\n', 'api:\n  generate_pages: false\n'),
        encoding='utf-8',
    )
    (example / 'docs/index.md').write_text(
        '::: api python:example.add\nshow_source: false\n:::\n',
        encoding='utf-8',
    )
    result = compile_site(path)
    assert result.page_count == 2
    assert 'Source:' not in result.files['index.html'].decode()
    (example / 'docs/index.md').write_text(
        '{@api python:example.add}', encoding='utf-8'
    )
    with pytest.raises(BuildError, match='No generated API page'):
        compile_site(path)


@typechecked
def test_unsupported_nodes_fail_closed(tmp_path: Path) -> None:
    """
    title: Reject unsupported nodes and namespace packages.
    parameters:
      tmp_path:
        description: Temporary directory provided by pytest.
    """
    with pytest.raises(BuildError, match='Unsupported declaration'):
        signature(object())
    with pytest.raises(BuildError, match='Unsupported declaration'):
        annotation_signature(object())
    with pytest.raises(BuildError, match='Unsupported declaration'):
        visit(object(), tmp_path)
    module = griffe.Module('namespace', filepath=[tmp_path])
    with pytest.raises(BuildError, match='No single source file'):
        source_path(module)
