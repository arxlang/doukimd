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
        description: Project configuration or temporary project directory.
      monkeypatch:
        description: Fixture for restoring patched objects after the test.
    """
    config = project / 'doukimd.yaml'
    before = build_site(config)
    previous_html = before.files['index.html']
    (project / 'docs/index.md').write_text('# Changed', encoding='utf-8')
    rename = Path.rename

    @typechecked
    def fail_publish(path: Path, target: Path) -> Path:
        """
        title: Simulate a filesystem failure during publication.
        parameters:
          path:
            description: Path or qualified declaration name to resolve.
          target:
            description: Target name or route to resolve.
        returns:
          description: Unreachable result when the simulated failure is raised.
        """
        if path.name == 'site' and target.name == 'build':
            raise OSError('simulated publication failure')
        return rename(path, target)

    monkeypatch.setattr(Path, 'rename', fail_publish)
    with pytest.raises(OSError, match='simulated'):
        build_site(config)
    assert (project / 'build/index.html').read_bytes() == previous_html
    assert not list(project.glob('.doukimd-*'))


@pytest.mark.parametrize('failure', ['theme', 'page-write', 'manifest-write'])
@pytest.mark.parametrize('existing', [False, True])
@typechecked
def test_staging_failure_preserves_output(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    existing: bool,
) -> None:
    """
    title: Discard partial staging after late render and disk failures.
    parameters:
      project:
        description: Temporary documentation project.
      monkeypatch:
        description: Fixture restoring patched filesystem methods.
      failure:
        description: Rendering or artifact write to interrupt.
      existing:
        description: Whether a successful site already exists.
    """
    config = project / 'doukimd.yaml'
    output = project / 'build'
    previous: dict[str, bytes] = {}
    if existing:
        previous = dict(build_site(config).files)
    (project / 'docs/index.md').write_text('# Changed\n')
    (project / 'docs/z-last.md').write_text('# Last\n')
    config.write_text(config.read_text() + 'theme:\n  directory: theme\n')
    (project / 'theme').mkdir()
    (project / 'theme/page.html').write_text(
        '{% if page.url == "z-last.html" %}{{ missing }}{% endif %}'
        if failure == 'theme'
        else '{{ content }}'
    )
    write_bytes = Path.write_bytes
    staged_pages: list[str] = []

    @typechecked
    def write(path: Path, data: bytes) -> int:
        """
        title: Observe staged pages and simulate an exhausted output disk.
        parameters:
          path:
            description: Artifact destination in the staging directory.
          data:
            description: Generated artifact bytes.
        returns:
          description: Number of bytes written before any simulated failure.
        """
        assert path.is_relative_to(project)
        assert not path.is_relative_to(output)
        if path.name == 'z-last.html' or path.name == MANIFEST:
            assert staged_pages == (
                ['index.html', 'z-last.html']
                if path.name == MANIFEST
                else ['index.html']
            )
            assert {
                item.relative_to(output).as_posix(): item.read_bytes()
                for item in output.rglob('*')
                if item.is_file()
            } == previous
            if (failure == 'page-write' and path.name == 'z-last.html') or (
                failure == 'manifest-write' and path.name == MANIFEST
            ):
                raise OSError('simulated disk full')
        if path.suffix == '.html':
            staged_pages.append(path.name)
        return write_bytes(path, data)

    monkeypatch.setattr(Path, 'write_bytes', write)
    with pytest.raises((BuildError, OSError)):
        build_site(config)
    assert staged_pages
    assert not list(project.glob('.doukimd-*'))
    assert {
        item.relative_to(output).as_posix(): item.read_bytes()
        for item in output.rglob('*')
        if item.is_file()
    } == previous
    assert output.exists() == existing


@pytest.mark.parametrize('manifest', ['[]', '{"generator": "other"}'])
@typechecked
def test_invalid_output_manifest(project: Path, manifest: str) -> None:
    """
    title: Treat malformed ownership metadata as a build error.
    parameters:
      project:
        description: Project configuration or temporary project directory.
      manifest:
        description: Build manifest describing managed output files.
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
        description: Project configuration or temporary project directory.
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
        description: Project configuration or temporary project directory.
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
        description: Project configuration or temporary project directory.
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
        description: Project configuration or temporary project directory.
      location:
        description: Source location used in diagnostics.
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
        description: Project configuration or temporary project directory.
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
