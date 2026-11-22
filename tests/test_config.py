"""
title: Validate configuration at the earliest boundary.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pydantic import ValidationError
from typeguard import TypeCheckError

from doukimd.config import load_config, load_data, project_path, read_yaml
from doukimd.errors import BuildError
from doukimd.models import Config, Page, PageSettings
from doukimd.runtime import typechecked


@pytest.mark.parametrize(
    'text',
    [
        'a: 1\na: 2',
        'nested:\n  a: 1\n  a: 2',
        '[1, 2]',
        'null',
        '42',
        '? [a, b]\n: c',
        'date: 2026-01-01',
        'a: !!python/object:evil {}',
        'a: [',
    ],
)
@typechecked
def test_invalid_yaml(text: str, tmp_path: Path) -> None:
    """
    title: Reject malformed and ambiguous metadata.
    parameters:
      text:
        description: Text content to process.
      tmp_path:
        description: Temporary directory provided by pytest.
    """
    with pytest.raises(BuildError, match='metadata'):
        read_yaml(text, tmp_path / 'input.yaml')


@pytest.mark.parametrize(
    'extra',
    [
        'unknown: true',
        'schema_version: 2',
        'docs_dir: 5',
        'api:\n  sources:\n    - language: arx\n      modules: [demo]',
        'api:\n  generate_pages: "false"',
        'plugins: [test, test]',
        'site:\n  title: ""',
        'project:\n  name: ""',
    ],
)
@typechecked
def test_invalid_config(project: Path, extra: str) -> None:
    """
    title: Fail closed on unsupported configuration.
    parameters:
      project:
        description: Project configuration or temporary project directory.
      extra:
        description: Additional fixture settings or generated output files.
    """
    config = project / 'doukimd.yaml'
    # Replace sections for tests of nested validation.
    base = 'site:\n  title: Test\nproject:\n  name: test\n'
    if extra.startswith('site:'):
        base = 'project:\n  name: test\n'
    if extra.startswith('project:'):
        base = 'site:\n  title: Test\n'
    config.write_text(base + extra + '\n', encoding='utf-8')
    with pytest.raises(BuildError):
        load_config(config)


@typechecked
def test_missing_config_and_data(project: Path) -> None:
    """
    title: Report missing input files as structured failures.
    parameters:
      project:
        description: Project configuration or temporary project directory.
    """
    with pytest.raises(BuildError, match='config'):
        load_config(project / 'missing.yaml')
    config = Config(
        site={'title': 'Docs'},
        project={'name': 'test'},
        data={'missing': 'missing.yaml'},
    )
    with pytest.raises(BuildError, match='metadata'):
        load_data(project, config)


@pytest.mark.parametrize('value', ['../escape', '/tmp/escape'])
@typechecked
def test_paths_are_relative(tmp_path: Path, value: str) -> None:
    """
    title: Reject absolute paths and parent traversal.
    parameters:
      tmp_path:
        description: Temporary directory provided by pytest.
      value:
        description: Input value to validate or render.
    """
    with pytest.raises(BuildError, match='relative project path'):
        project_path(tmp_path, value)


@typechecked
def test_symlink_escape(tmp_path: Path) -> None:
    """
    title: Reject symlinks escaping a configured root.
    parameters:
      tmp_path:
        description: Temporary directory provided by pytest.
    """
    root = tmp_path / 'root'
    root.mkdir()
    link = root / 'outside'
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip('Symlink creation is unavailable')
    with pytest.raises(BuildError, match='escapes project'):
        project_path(root, 'outside/file')


@typechecked
def test_runtime_checks_all_collection_items() -> None:
    """
    title: Check arguments beyond the first collection item at runtime.
    """
    from doukimd.content import plan_pages

    config = Config(site={'title': 'Docs'}, project={'name': 'test'})
    good = Page('index.html', 'Home', '', PageSettings())
    with pytest.raises(TypeCheckError):
        plan_pages([good, 'invalid'], {}, config)  # type: ignore[list-item]
    with pytest.raises(TypeCheckError):
        read_yaml(42, Path('test.yaml'))  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        Page('index.html', 42, '', PageSettings())  # type: ignore[arg-type]


@typechecked
def test_yaml_merge_key_with_override(tmp_path: Path) -> None:
    """
    title: Allow explicit keys to override merged anchor defaults.
    parameters:
      tmp_path:
        description: Temporary directory provided by pytest.
    """
    text = 'base: &b\n  a: 1\n  b: 2\nderived:\n  <<: *b\n  a: 99\n'
    result = read_yaml(text, tmp_path / 'merge.yaml')
    assert result == {'base': {'a': 1, 'b': 2}, 'derived': {'a': 99, 'b': 2}}


@typechecked
def test_yaml_merge_key_without_override(tmp_path: Path) -> None:
    """
    title: Allow merge keys without explicit overrides.
    parameters:
      tmp_path:
        description: Temporary directory provided by pytest.
    """
    text = 'base: &b\n  a: 1\nderived:\n  <<: *b\n  c: 3\n'
    result = read_yaml(text, tmp_path / 'merge.yaml')
    assert result == {'base': {'a': 1}, 'derived': {'a': 1, 'c': 3}}


@typechecked
def test_yaml_real_duplicate_key_rejected(tmp_path: Path) -> None:
    """
    title: Reject explicit duplicate keys in plain mapping.
    parameters:
      tmp_path:
        description: Temporary directory provided by pytest.
    """
    text = 'x:\n  a: 1\n  a: 2\n'
    with pytest.raises(BuildError, match='Duplicate YAML key: a'):
        read_yaml(text, tmp_path / 'dup.yaml')


@typechecked
def test_yaml_duplicate_next_to_merge_key_rejected(tmp_path: Path) -> None:
    """
    title: Reject explicit duplicate keys written alongside a merge key.
    parameters:
      tmp_path:
        description: Temporary directory provided by pytest.
    """
    text = 'base: &b\n  x: 0\nderived:\n  <<: *b\n  a: 1\n  a: 2\n'
    with pytest.raises(BuildError, match='Duplicate YAML key: a'):
        read_yaml(text, tmp_path / 'dup_merge.yaml')


@typechecked
def test_yaml_merge_list_precedence(tmp_path: Path) -> None:
    """
    title: Preserve PyYAML precedence when merging a list of anchors.
    parameters:
      tmp_path:
        description: Temporary directory provided by pytest.
    """
    text = (
        'first: &first\n'
        '  key: from_first\n'
        '  shared: first_val\n'
        'second: &second\n'
        '  key: from_second\n'
        '  shared: second_val\n'
        'derived:\n'
        '  <<: [*first, *second]\n'
        '  own: explicit\n'
    )
    result = read_yaml(text, tmp_path / 'merge_list.yaml')
    assert result['derived'] == {
        'key': 'from_first',
        'shared': 'first_val',
        'own': 'explicit',
    }


@typechecked
def test_yaml_nested_mapping_merge_override(tmp_path: Path) -> None:
    """
    title: Allow merge key overrides in nested mappings.
    parameters:
      tmp_path:
        description: Temporary directory provided by pytest.
    """
    text = (
        'parent:\n'
        '  defaults: &d\n'
        '    item: 1\n'
        '    mode: auto\n'
        '  custom:\n'
        '    <<: *d\n'
        '    item: 42\n'
    )
    result = read_yaml(text, tmp_path / 'nested.yaml')
    assert result['parent']['custom'] == {'item': 42, 'mode': 'auto'}


@typechecked
def test_yaml_non_string_key_rejected(tmp_path: Path) -> None:
    """
    title: Reject non-string keys in explicit and merged mappings.
    parameters:
      tmp_path:
        description: Temporary directory provided by pytest.
    """
    text_explicit = '1: int_key\n'
    with pytest.raises(BuildError, match='YAML mapping keys must be strings'):
        read_yaml(text_explicit, tmp_path / 'non_str.yaml')
