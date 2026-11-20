"""
title: Navigation reuse without stale page state or changed rendered output.
"""

from __future__ import annotations

import tracemalloc

from pathlib import Path

import pytest

from click.testing import CliRunner
from jinja2 import Environment
from jinja2.runtime import Macro
from markupsafe import Markup

from doukimd.build import compile_site
from doukimd.cli import main
from doukimd.navigation_plan import NavigationView
from doukimd.runtime import typechecked
from doukimd.theme import NavigationFragments


@typechecked
def test_fragment_cache_preserves_every_page(
    example: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    title: Compare cached and uncached HTML across modules and directories.
    parameters:
      example:
        description: Copy of the complete example project.
      monkeypatch:
        description: Fixture for restoring patched objects after the test.
    """
    config = example / 'doukimd.yaml'
    config.write_text(
        config.read_text().replace('[example]', '[example, other]')
    )
    (example / 'src/other.py').write_text(
        '"""title: Other module."""\n'
        'def extra() -> None:\n    """title: Extra callable."""\n'
    )
    (example / 'docs/nested').mkdir()
    (example / 'docs/nested/index.md').write_text('# Nested\n')
    cached = compile_site(config)
    hits = 0
    original = NavigationFragments.render

    @typechecked
    def uncached(
        self: NavigationFragments,
        macro: Macro,
        item: NavigationView,
        group_id: str,
        opened: bool,
    ) -> str:
        """
        title: Verify each cached fragment against a fresh macro
          invocation.
        parameters:
          self:
            description: Instance bound to the patched helper.
          macro:
            description: Theme macro used to render a navigation
              fragment.
          item:
            description: Declaration or navigation entry being rendered.
          group_id:
            description: Identifier that keeps separate accordion
              menus independent.
          opened:
            description: Whether the accordion branch is expanded.
        returns:
          description: Freshly rendered fragment matching the cached
            output.
        """
        nonlocal hits
        key = (id(item.node), id(item.selection.urls), group_id, opened)
        hits += key in self.fragments

        @typechecked
        def attribute(view: NavigationView, location: bool) -> str:
            """
            title: Render selection attributes directly from the
              current view.
            parameters:
              view:
                description: Page-specific navigation links and selection
                  state.
              location:
                description: Source location used in diagnostics.
            returns:
              description: Rendered attribute or registered selection
                placeholder.
            """
            if view.current:
                return Markup(' aria-current="page"')
            if location and view.active:
                return Markup(' aria-current="location"')
            return ''

        expected = macro(item, group_id, opened, attribute)
        assert original(self, macro, item, group_id, opened) == expected
        return expected

    monkeypatch.setattr(NavigationFragments, 'render', uncached)
    fresh = compile_site(config)
    assert hits > 0
    assert cached.files == fresh.files
    assert cached.page_count == fresh.page_count


@typechecked
def test_fragment_cache_is_bounded(example: Path) -> None:
    """
    title: Evict old inactive fragments and bypass selected branches.
    parameters:
      example:
        description: Copy of the complete example project.
    """
    from doukimd.api import collect_api
    from doukimd.config import load_config
    from doukimd.content import discover_pages, plan_pages
    from doukimd.indexes import ApiIndex, SiteIndex
    from doukimd.navigation_plan import NavigationPlan

    config = load_config(example / 'doukimd.yaml')
    inventory = collect_api(example, config)
    pages = discover_pages(example, config)
    routes = plan_pages(pages, inventory, config)
    plan = NavigationPlan(
        SiteIndex(pages), ApiIndex(inventory, routes), config
    )
    item = plan.navigation(pages[0])[-1]
    assert not item.active
    cache = NavigationFragments()
    macro = (
        Environment()
        .from_string(
            '{% macro fragment(item, group_id, opened, attribute) %}'
            'fragment{% endmacro %}'
        )
        .module.fragment
    )
    for number in range(2050):
        cache.render(macro, item, str(number), False)
    assert len(cache.fragments) == 2048
    assert len(cache.slots) == 2048
    assert (id(item.node), id(item.selection.urls), '0', False) not in (
        cache.fragments
    )


@pytest.mark.parametrize('command', ['build', 'check'])
@typechecked
def test_cli_does_not_buffer_rendered_site(
    project: Path, command: str
) -> None:
    """
    title: Keep peak allocations below the size of a generated site.
    parameters:
      project:
        description: Temporary documentation project.
      command:
        description: CLI operation to measure.
    """
    # Tiny Markdown pages expand through a real theme to 32 MiB of unique
    # output. Retaining the encoded pages exceeds this budget by itself.
    config = project / 'doukimd.yaml'
    config.write_text(
        config.read_text()
        + 'theme:\n  directory: theme\nsearch:\n  enabled: false\n'
    )
    (project / 'theme').mkdir()
    (project / 'theme/page.html').write_text(
        '{{ page.url }}{{ "x" * 1048576 }}'
    )
    for number in range(31):
        (project / f'docs/page-{number}.md').write_text(f'# Page {number}\n')
    tracemalloc.start()
    try:
        result = CliRunner().invoke(main, [command, '--config', str(config)])
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert result.exit_code == 0, result.output
    assert '32 pages' in result.output
    assert peak < 16 * 1024**2, f'Peak allocation: {peak / 1024**2:.1f} MiB'
    if command == 'build':
        output = project / 'build'
        assert len(list(output.glob('*.html'))) == 32
        assert sum(path.stat().st_size for path in output.glob('*.html')) > (
            32 * 1024**2
        )
    else:
        assert not (project / 'build').exists()
    assert not list(project.glob('.doukimd-*'))
