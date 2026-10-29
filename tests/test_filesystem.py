"""
title: Filesystem and failure recovery boundaries.
"""

from __future__ import annotations

import json

from pathlib import Path

import pytest

from doukimd.build import MANIFEST, build_site, compile_site
from doukimd.errors import BuildError
from doukimd.runtime import typechecked


@typechecked
def test_commit_failure_restores_previous_site(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    title: Restore the old site if publishing the staged build fails.
    parameters:
      project:
        type: Path
      monkeypatch:
        type: pytest.MonkeyPatch
    """
    config = project / 'doukimd.yaml'
    before = build_site(config)
    (project / 'docs/index.md').write_text('# Changed', encoding='utf-8')
    rename = Path.rename

    @typechecked
    def fail_publish(path: Path, target: Path) -> Path:
        """
        title: Simulate a filesystem failure during publication.
        parameters:
          path:
            type: Path
          target:
            type: Path
        returns:
          type: Path
        """
        if path.name == 'site' and target.name == 'build':
            raise OSError('simulated publication failure')
        return rename(path, target)

    monkeypatch.setattr(Path, 'rename', fail_publish)
    with pytest.raises(OSError, match='simulated'):
        build_site(config)
    assert (project / 'build/index.html').read_bytes() == before.files[
        'index.html'
    ]


@pytest.mark.parametrize('manifest', ['[]', '{"generator": "other"}'])
@typechecked
def test_invalid_output_manifest(project: Path, manifest: str) -> None:
    """
    title: Treat malformed ownership metadata as a build error.
    parameters:
      project:
        type: Path
      manifest:
        type: str
    """
    (project / 'build').mkdir()
    (project / 'build' / MANIFEST).write_text(manifest, encoding='utf-8')
    with pytest.raises(BuildError, match='Invalid output manifest'):
        build_site(project / 'doukimd.yaml')


@typechecked
def test_missing_directories_and_empty_site(project: Path) -> None:
    """
    title: Report missing inputs and sites with no renderable pages.
    parameters:
      project:
        type: Path
    """
    config = project / 'doukimd.yaml'
    (project / 'docs/index.md').unlink()
    with pytest.raises(BuildError, match='no pages'):
        compile_site(config)
    (project / 'docs').rmdir()
    with pytest.raises(BuildError, match='directory is missing'):
        compile_site(config)
    (project / 'docs').mkdir()
    (project / 'docs/index.md').write_text('# Home', encoding='utf-8')
    config.write_text(
        config.read_text() + 'theme:\n  directory: missing\n',
        encoding='utf-8',
    )
    with pytest.raises(BuildError, match='Theme directory is missing'):
        compile_site(config)


@typechecked
def test_output_file_is_not_a_directory(project: Path) -> None:
    """
    title: Preserve an output path already occupied by a file.
    parameters:
      project:
        type: Path
    """
    target = project / 'build'
    target.write_text('keep', encoding='utf-8')
    with pytest.raises(BuildError, match='not a directory'):
        build_site(project / 'doukimd.yaml')
    assert target.read_text() == 'keep'


@typechecked
def test_case_collisions_are_portable(project: Path) -> None:
    """
    title: Reject routes that collide on case-insensitive filesystems.
    parameters:
      project:
        type: Path
    """
    other = project / 'docs/INDEX.md'
    if other.exists():
        pytest.skip('The filesystem is case insensitive')
    other.write_text('# Upper', encoding='utf-8')
    with pytest.raises(BuildError, match='Duplicate route'):
        compile_site(project / 'doukimd.yaml')


@pytest.mark.parametrize('location', ['page', 'asset', 'include'])
@typechecked
def test_source_symlinks_stay_inside_roots(
    project: Path, location: str
) -> None:
    """
    title: Refuse reads through source or include symlinks outside their root.
    parameters:
      project:
        type: Path
      location:
        type: str
    """
    outside = project / 'outside.md'
    outside.write_text('must not read', encoding='utf-8')
    if location == 'page':
        link = project / 'docs/linked.md'
    elif location == 'asset':
        (project / 'docs/assets').mkdir()
        link = project / 'docs/assets/linked.txt'
    else:
        (project / 'includes').mkdir()
        link = project / 'includes/linked.md'
        (project / 'docs/index.md').write_text(
            '---\nrender: jinja\n---\n{% include "linked.md" %}',
            encoding='utf-8',
        )
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip('Symlink creation is unavailable')
    with pytest.raises(BuildError, match='escapes'):
        compile_site(project / 'doukimd.yaml')


@typechecked
def test_invalid_encoding_and_empty_metadata(project: Path) -> None:
    """
    title: Accept empty front matter and diagnose non-UTF-8 content.
    parameters:
      project:
        type: Path
    """
    page = project / 'docs/index.md'
    page.write_text('---\n---\n# Empty metadata', encoding='utf-8')
    result = compile_site(project / 'doukimd.yaml')
    assert json.loads(result.files['search.json'])[0]['title'] == (
        'Empty metadata'
    )
    page.write_bytes(b'\xff')
    with pytest.raises(BuildError, match='discovery'):
        compile_site(project / 'doukimd.yaml')
