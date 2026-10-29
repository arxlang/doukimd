"""
title: Explicit plugin loading and validated context namespaces.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from doukimd.build import compile_site
from doukimd.errors import BuildError
from doukimd.models import Config
from doukimd.plugins import hookimpl
from doukimd.runtime import typechecked


@typechecked
def test_plugin_context(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    title: Expose validated plugin data only under its own namespace.
    parameters:
      project:
        type: Path
      monkeypatch:
        type: pytest.MonkeyPatch
    """

    class Provider:
        """
        title: Supply one context namespace.
        """

        @hookimpl
        @typechecked
        def doukimd_context(self, config: Config) -> dict[str, object]:
            """
            title: Return project-specific template data.
            parameters:
              config:
                type: Config
            returns:
              type: dict[str, object]
            """
            return {'message': config.project.name}

    provider = Provider()
    entry = SimpleNamespace(name='example', load=lambda: provider)
    monkeypatch.setattr(
        'doukimd.plugins.entry_points', lambda **kwargs: [entry]
    )
    path = project / 'doukimd.yaml'
    path.write_text(
        path.read_text() + 'plugins: [example]\n', encoding='utf-8'
    )
    (project / 'docs/index.md').write_text(
        '---\nrender: jinja\n---\n{{ plugins.example.message }}',
        encoding='utf-8',
    )
    html = compile_site(path).files['index.html'].decode()
    assert '<p>test</p>' in html


@pytest.mark.parametrize('mode', ['missing', 'empty', 'invalid', 'unknown'])
@typechecked
def test_plugin_failures(
    project: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """
    title: Reject unavailable plugins and invalid extension results.
    parameters:
      project:
        type: Path
      monkeypatch:
        type: pytest.MonkeyPatch
      mode:
        type: str
    """

    class InvalidProvider:
        """
        title: Return a value outside the JSON data contract.
        """

        @hookimpl
        @typechecked
        def doukimd_context(self, config: Config) -> dict[str, object]:
            """
            title: Supply deliberately unsupported data.
            parameters:
              config:
                type: Config
            returns:
              type: dict[str, object]
            """
            return {'path': Path('not-json')}

    class UnknownHook:
        """
        title: Expose a hook the host does not support.
        """

        @hookimpl
        @typechecked
        def doukimd_unknown(self) -> None:
            """
            title: Exercise plugin specification validation.
            """

    provider = (
        InvalidProvider()
        if mode == 'invalid'
        else UnknownHook()
        if mode == 'unknown'
        else object()
    )
    entry = SimpleNamespace(name='example', load=lambda: provider)
    monkeypatch.setattr(
        'doukimd.plugins.entry_points',
        lambda **kwargs: [] if mode == 'missing' else [entry],
    )
    path = project / 'doukimd.yaml'
    path.write_text(
        path.read_text() + 'plugins: [example]\n', encoding='utf-8'
    )
    with pytest.raises(BuildError, match='plugins'):
        compile_site(path)
