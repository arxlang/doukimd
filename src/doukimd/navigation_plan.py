"""
title: Prepare immutable menu structure once and select page-local states.
"""

from __future__ import annotations

import posixpath

from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
from typing import Literal, Mapping
from urllib.parse import quote, unquote, urlsplit

from public import private

from doukimd.indexes import ApiIndex, SiteIndex
from doukimd.models import Config, NavigationItem, Page, PageSettings
from doukimd.navigation import (
    automatic_navigation,
    configured_items,
    module_navigation,
    sidebar_for_page,
)
from doukimd.runtime import typechecked


@private
@typechecked
@dataclass(frozen=True)
class MenuNode:
    """
    title: Store a menu entry independently of any current page.
    attributes:
      identifier:
        type: int
      title:
        type: str
      url:
        type: str | None
      kind:
        type: str | None
      layout:
        type: Literal[nested, modules]
      children:
        type: tuple[MenuNode, Ellipsis]
    """

    identifier: int
    title: str
    url: str | None
    kind: str | None
    layout: Literal['nested', 'modules']
    children: tuple[MenuNode, ...]


@private
@typechecked
def relative_url(url: str | None, directory: str) -> str | None:
    """
    title: >-
      Rebase an already validated root-relative URL without losing escaping.
    parameters:
      url:
        type: str | None
      directory:
        type: str
    returns:
      type: str | None
    """
    if url is None:
        return None
    target = urlsplit(url)
    if target.scheme or target.netloc:
        return url
    path = quote(posixpath.relpath(unquote(target.path), directory))
    if target.path.endswith('/'):
        path = './' if path == '.' else path + '/'
    return (
        path
        + (f'?{target.query}' if target.query else '')
        + (f'#{target.fragment}' if target.fragment else '')
    )


@private
@typechecked
class PreparedMenu:
    """
    title: Freeze menu links and index the nodes affected by a page selection.
    attributes:
      roots:
        type: tuple[MenuNode, Ellipsis]
      nodes:
        type: Mapping[int, MenuNode]
      parents:
        type: Mapping[int, int]
      current_nodes:
        type: Mapping[str, tuple[int, Ellipsis]]
      ancestor_nodes:
        type: Mapping[str, tuple[int, Ellipsis]]
      module_nodes:
        type: Mapping[str, tuple[int, Ellipsis]]
      prefixes:
        type: Mapping[str, tuple[int, Ellipsis]]
      api_nodes:
        type: tuple[int, Ellipsis]
      relative_urls:
        type: dict[str, Mapping[int, str | None]]
    """

    roots: tuple[MenuNode, ...]
    nodes: Mapping[int, MenuNode]
    parents: Mapping[int, int]
    current_nodes: Mapping[str, tuple[int, ...]]
    ancestor_nodes: Mapping[str, tuple[int, ...]]
    module_nodes: Mapping[str, tuple[int, ...]]
    prefixes: Mapping[str, tuple[int, ...]]
    api_nodes: tuple[int, ...]
    relative_urls: dict[str, Mapping[int, str | None]]

    def __init__(
        self,
        items: list[NavigationItem],
        site: SiteIndex,
        header: bool,
        configured: bool,
    ) -> None:
        """
        title: >-
          Capture checked menu entries without sharing mutable child lists.
        parameters:
          items:
            type: list[NavigationItem]
          site:
            type: SiteIndex
          header:
            type: bool
          configured:
            type: bool
        """
        nodes: dict[int, MenuNode] = {}
        parents: dict[int, int] = {}
        current: dict[str, list[int]] = {}
        ancestors: dict[str, list[int]] = {}
        modules: dict[str, list[int]] = {}
        prefixes: dict[str, list[int]] = {}
        api_nodes: list[int] = []
        next_identifier = 0

        @typechecked
        def freeze(item: NavigationItem, parent: int | None) -> MenuNode:
            """
            title: Freeze one entry and register its selection rules.
            parameters:
              item:
                type: NavigationItem
              parent:
                type: int | None
            returns:
              type: MenuNode
            """
            nonlocal next_identifier
            identifier = next_identifier
            next_identifier += 1
            if parent is not None:
                parents[identifier] = parent
            node = MenuNode(
                identifier,
                item.title,
                item.url,
                item.kind,
                item.layout,
                tuple(freeze(child, identifier) for child in item.children),
            )
            nodes[identifier] = node
            target_page = None
            if item.url is not None:
                target = urlsplit(item.url)
                if not target.scheme and not target.netloc:
                    path = unquote(target.path)
                    route = path + 'index.html' if path.endswith('/') else path
                    target_page = site.by_route.get(posixpath.normpath(route))
            if target_page is None:
                return node
            scoped_sidebar = (
                not header
                and item.layout == 'modules'
                and target_page.route != 'api/index.html'
            )
            if not scoped_sidebar:
                current.setdefault(target_page.route, []).append(identifier)
            symbol = target_page.symbol
            if symbol is not None:
                if header and (
                    item.kind is not None or item.layout == 'modules'
                ):
                    ancestors.setdefault(symbol, []).append(identifier)
                elif item.kind == 'module':
                    modules.setdefault(symbol, []).append(identifier)
                elif item.kind is not None:
                    ancestors.setdefault(symbol, []).append(identifier)
            if (
                header
                and item.layout == 'modules'
                and target_page.route == 'api/index.html'
            ):
                api_nodes.append(identifier)
            if configured and item.kind is None and item.layout != 'modules':
                section = posixpath.dirname(target_page.route)
                if section and target_page.route.endswith('/index.html'):
                    prefixes.setdefault(section + '/', []).append(identifier)
            return node

        self.roots = tuple(freeze(item, None) for item in items)
        self.nodes = MappingProxyType(nodes)
        self.parents = MappingProxyType(parents)
        self.current_nodes = MappingProxyType(
            {k: tuple(v) for k, v in current.items()}
        )
        self.ancestor_nodes = MappingProxyType(
            {k: tuple(v) for k, v in ancestors.items()}
        )
        self.module_nodes = MappingProxyType(
            {k: tuple(v) for k, v in modules.items()}
        )
        self.prefixes = MappingProxyType(
            {k: tuple(v) for k, v in prefixes.items()}
        )
        self.api_nodes = tuple(api_nodes)
        self.relative_urls = {}

    def select(self, page: Page, api: ApiIndex) -> tuple[NavigationView, ...]:
        """
        title: Resolve one page's flags while reusing all stable menu links.
        parameters:
          page:
            type: Page
          api:
            type: ApiIndex
        returns:
          type: tuple[NavigationView, Ellipsis]
        """
        if not self.roots:
            return ()
        selection = MenuSelection(self, page, api)
        return tuple(NavigationView(node, selection) for node in self.roots)


@private
@typechecked
@dataclass(frozen=True, init=False)
class MenuSelection:
    """
    title: Keep current and active flags isolated to one rendered page.
    attributes:
      current:
        type: frozenset[int]
      active:
        type: frozenset[int]
      urls:
        type: Mapping[int, str | None]
    """

    current: frozenset[int]
    active: frozenset[int]
    urls: Mapping[int, str | None]

    def __init__(self, menu: PreparedMenu, page: Page, api: ApiIndex) -> None:
        """
        title: Select route matches, symbol ancestors, and the closest module.
        parameters:
          menu:
            type: PreparedMenu
          page:
            type: Page
          api:
            type: ApiIndex
        """
        current = frozenset(menu.current_nodes.get(page.route, ()))
        active = set(current)
        for prefix, identifiers in menu.prefixes.items():
            if page.route.startswith(prefix):
                active.update(identifiers)
        if page.symbol is not None:
            chain = api.ancestors(page.symbol)
            for symbol in chain:
                active.update(menu.ancestor_nodes.get(symbol.identifier, ()))
            module = next(
                (item for item in chain if item.kind == 'module'), None
            )
            if module is not None:
                active.update(menu.module_nodes.get(module.identifier, ()))
            active.update(menu.api_nodes)
        pending = list(active)
        while pending:
            parent = menu.parents.get(pending.pop())
            if parent is not None and parent not in active:
                active.add(parent)
                pending.append(parent)
        directory = posixpath.dirname(page.route) or '.'
        urls = menu.relative_urls.get(directory)
        if urls is None:
            urls = MappingProxyType(
                {
                    identifier: relative_url(node.url, directory)
                    for identifier, node in menu.nodes.items()
                }
            )
            menu.relative_urls[directory] = urls
        object.__setattr__(self, 'current', current)
        object.__setattr__(self, 'active', frozenset(active))
        object.__setattr__(self, 'urls', urls)


@private
@typechecked
@dataclass(frozen=True)
class NavigationView:
    """
    title: >-
      Expose the theme's existing menu fields through a read-only page view.
    attributes:
      node:
        type: MenuNode
      selection:
        type: MenuSelection
    """

    node: MenuNode
    selection: MenuSelection

    @property
    def title(self) -> str:
        """
        title: Return the configured label.
        returns:
          type: str
        """
        return self.node.title

    @property
    def url(self) -> str | None:
        """
        title: Return a link relative to the current output directory.
        returns:
          type: str | None
        """
        return self.selection.urls[self.node.identifier]

    @property
    def kind(self) -> str | None:
        """
        title: Return the API declaration kind when present.
        returns:
          type: str | None
        """
        return self.node.kind

    @property
    def layout(self) -> Literal['nested', 'modules']:
        """
        title: Return the menu's rendering strategy.
        returns:
          type: Literal[nested, modules]
        """
        return self.node.layout

    @property
    def current(self) -> bool:
        """
        title: Identify exact page matches.
        returns:
          type: bool
        """
        return self.node.identifier in self.selection.current

    @property
    def active(self) -> bool:
        """
        title: Identify the active branch without traversing unrelated nodes.
        returns:
          type: bool
        """
        return self.node.identifier in self.selection.active

    @cached_property
    def children(self) -> tuple[NavigationView, ...]:
        """
        title: Materialize immutable children once when the theme needs them.
        returns:
          type: tuple[NavigationView, Ellipsis]
        """
        return tuple(
            NavigationView(child, self.selection)
            for child in self.node.children
        )


@private
@typechecked
class NavigationPlan:
    """
    title: >-
      Resolve all configured targets once, then prepare only selected menus.
    attributes:
      site:
        type: SiteIndex
      api:
        type: ApiIndex
      config:
        type: Config
      automatic:
        type: list[NavigationItem]
      sidebars:
        type: dict[str, list[NavigationItem]]
      menus:
        type: dict[str | None, PreparedMenu]
      origin:
        type: Page
      navbar:
        type: PreparedMenu | None
    """

    site: SiteIndex
    api: ApiIndex
    config: Config
    automatic: list[NavigationItem]
    sidebars: dict[str, list[NavigationItem]]
    menus: dict[str | None, PreparedMenu]
    origin: Page
    navbar: PreparedMenu | None

    def __init__(self, site: SiteIndex, api: ApiIndex, config: Config) -> None:
        """
        title: Validate hidden menus too, before rendering any page.
        parameters:
          site:
            type: SiteIndex
          api:
            type: ApiIndex
          config:
            type: Config
        """
        self.site = site
        self.api = api
        self.config = config
        self.origin = Page(
            '__doukimd_navigation__.html', '', '', PageSettings()
        )
        self.automatic = automatic_navigation(site, self.origin, api)
        self.sidebars = {
            sidebar.id: configured_items(
                sidebar.items, self.automatic, site, self.origin, api
            )
            for sidebar in config.navigation.sidebars
        }
        self.menus = {}
        self.navbar = None

    def navigation(self, page: Page) -> tuple[NavigationView, ...]:
        """
        title: Return the selected sidebar with page-local state.
        parameters:
          page:
            type: Page
        returns:
          type: tuple[NavigationView, Ellipsis]
        """
        selected = sidebar_for_page(self.config, page)
        if page.settings.sidebar is False or page.settings.layout == 'landing':
            return ()
        if selected is None and self.config.navigation.sidebars:
            return ()
        key = selected.id if selected is not None else None
        if key not in self.menus:
            items = self.sidebars[key] if key is not None else self.automatic
            flattened = [module_navigation(item) for item in items]
            self.menus[key] = PreparedMenu(
                flattened, self.site, header=False, configured=key is not None
            )
        return self.menus[key].select(page, self.api)

    def header(self, page: Page) -> tuple[NavigationView, ...]:
        """
        title: Return top-level menus with page-local links and state.
        parameters:
          page:
            type: Page
        returns:
          type: tuple[NavigationView, Ellipsis]
        """
        if self.navbar is None:
            items = configured_items(
                self.config.navigation.navbar,
                self.automatic,
                self.site,
                self.origin,
                self.api,
                expand_api=False,
            )
            self.navbar = PreparedMenu(
                items, self.site, header=True, configured=True
            )
        return self.navbar.select(page, self.api)
