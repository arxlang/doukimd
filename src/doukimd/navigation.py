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


@private
@typechecked
def symbol_navigation(
    identifier: str,
    current: Page,
    symbols: dict[str, Page],
    inventory: dict[str, ApiSymbol],
) -> NavigationItem:
    """
    title: Preserve declaration parentage in the API navigation tree.
    parameters:
      identifier:
        type: str
      current:
        type: Page
      symbols:
        type: dict[str, Page]
      inventory:
        type: dict[str, ApiSymbol]
    returns:
      type: NavigationItem
    """
    children = [
        symbol_navigation(name, current, symbols, inventory)
        for name in sorted(symbols)
        if inventory[name].parent == identifier
    ]
    return navigation_item(symbols[identifier], current, children)


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
    navigation: list[NavigationItem] = []
    for page in pages:
        if page.symbol is not None:
            continue
        children: list[NavigationItem] = []
        if page.route == 'api/index.html' and page.source is None:
            children = [
                symbol_navigation(name, current, symbols, inventory)
                for name in sorted(symbols)
                if inventory[name].parent not in symbols
            ]
        navigation.append(navigation_item(page, current, children))
    return navigation
