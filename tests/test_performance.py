"""
title: Navigation reuse without stale page state or changed rendered output.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jinja2 import Environment
from jinja2.runtime import Macro
from markupsafe import Markup

from doukimd.build import compile_site
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
        type: Path
      monkeypatch:
        type: pytest.MonkeyPatch
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
        title: Verify each cached fragment against a fresh macro invocation.
        parameters:
          self:
            type: NavigationFragments
          macro:
            type: Macro
          item:
            type: NavigationView
          group_id:
            type: str
          opened:
            type: bool
        returns:
          type: str
        """
        nonlocal hits
        key = (id(item.node), id(item.selection.urls), group_id, opened)
        hits += key in self.fragments

        @typechecked
        def attribute(view: NavigationView, location: bool) -> str:
            """
            title: Render selection attributes directly from the current view.
            parameters:
              view:
                type: NavigationView
              location:
                type: bool
            returns:
              type: str
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
        type: Path
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
