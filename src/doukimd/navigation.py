"""
title: Build theme-independent navigation from planned pages and symbols.
"""

from __future__ import annotations

import posixpath

from public import private, public

from doukimd.models import ApiSymbol, NavigationItem, Page
from doukimd.runtime import typechecked


@private
@typechecked
def navigation_item(
    target: Page, current: Page, children: list[NavigationItem]
) -> NavigationItem:
    """
    title: Resolve a navigation URL and active state against the current page.
    parameters:
      target:
        type: Page
      current:
        type: Page
      children:
        type: list[NavigationItem]
    returns:
      type: NavigationItem
    """
    selected = target.route == current.route
    url = posixpath.relpath(
        target.route, posixpath.dirname(current.route) or '.'
    )
    if target.route == 'api/index.html' and target.source is None:
        url = url.removesuffix('index.html') or './'
    return NavigationItem(
        title=target.title,
        url=url,
        current=selected,
        active=selected or any(item.active for item in children),
        children=children,
    )


@public
@typechecked
def build_navigation(
    pages: list[Page], current: Page, inventory: dict[str, ApiSymbol]
) -> list[NavigationItem]:
    """
    title: Gather generated references under one API Docs menu entry.
    parameters:
      pages:
        type: list[Page]
      current:
        type: Page
      inventory:
        type: dict[str, ApiSymbol]
    returns:
      type: list[NavigationItem]
    """
    symbols = {page.symbol: page for page in pages if page.symbol is not None}
    by_parent: dict[str | None, list[str]] = {}
    for name in sorted(symbols):
        parent = inventory[name].parent
        by_parent.setdefault(parent if parent in symbols else None, []).append(
            name
        )

    @typechecked
    def symbol_navigation(name: str) -> NavigationItem:
        """
        title: Walk the indexed symbol tree.
        parameters:
          name:
            type: str
        returns:
          type: NavigationItem
        """
        children = [
            symbol_navigation(child) for child in by_parent.get(name, [])
        ]
        return navigation_item(symbols[name], current, children).model_copy(
            update={'kind': inventory[name].kind}
        )

    navigation: list[NavigationItem] = []
    for page in pages:
        if page.symbol is not None:
            continue
        children: list[NavigationItem] = []
        if page.route == 'api/index.html' and page.source is None:
            children = [
                symbol_navigation(name) for name in by_parent.get(None, [])
            ]
        navigation.append(navigation_item(page, current, children))
    return navigation
