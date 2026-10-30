"""
title: Build theme-independent navigation from planned pages and symbols.
"""

from __future__ import annotations

import posixpath

from urllib.parse import quote, unquote, urlsplit

from public import private, public

from doukimd.errors import BuildError
from doukimd.models import (
    ApiSymbol,
    Config,
    NavEntry,
    NavigationItem,
    Page,
    SidebarSettings,
)
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
        url=quote(url),
        current=selected,
        active=selected or any(item.active for item in children),
        children=children,
    )


@private
@typechecked
def automatic_navigation(
    pages: list[Page],
    current: Page,
    inventory: dict[str, ApiSymbol],
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
        symbol = inventory[name]
        title = symbols[name].title
        if symbol.kind == 'module' and symbol.parent not in symbols:
            qualified = symbol.identifier.rsplit(':', 1)[-1]
            title = (
                f'{symbol.source_name} / {qualified}'
                if symbol.source_name
                else qualified
            )
        return navigation_item(symbols[name], current, children).model_copy(
            update={'kind': symbol.kind, 'title': title}
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
        item = navigation_item(page, current, children)
        if page.route == 'api/index.html' and page.source is None:
            item = item.model_copy(update={'layout': 'modules'})
        navigation.append(item)
    return navigation


@private
@typechecked
def module_navigation(item: NavigationItem) -> NavigationItem:
    """
    title: Keep a stable module list with one level of declaration links.
    parameters:
      item:
        type: NavigationItem
    returns:
      type: NavigationItem
    """
    if item.layout != 'modules':
        return item.model_copy(
            update={
                'children': [
                    module_navigation(child) for child in item.children
                ]
            }
        )
    modules: list[NavigationItem] = []

    @typechecked
    def gather(module: NavigationItem, title: str, prefix: str) -> None:
        """
        title: Flatten submodules while keeping class members in their pages.
        parameters:
          module:
            type: NavigationItem
          title:
            type: str
          prefix:
            type: str
        """
        if module.kind != 'module':
            raise BuildError(
                'navigation', f'Unsupported API root kind: {module.kind}'
            )
        members: list[NavigationItem] = []
        for child in module.children:
            if child.kind == 'module':
                continue
            if child.kind not in {
                'class',
                'function',
                'method',
                'property',
                'attribute',
                'enum-member',
                'type-alias',
            }:
                raise BuildError(
                    'navigation', f'Unsupported API kind: {child.kind}'
                )
            members.append(child.model_copy(update={'children': []}))
        modules.append(
            module.model_copy(update={'title': title, 'children': members})
        )
        for child in module.children:
            if child.kind == 'module':
                name = f'{prefix}.{child.title}' if prefix else child.title
                gather(child, name, name)

    for root in item.children:
        gather(root, root.title, root.title if len(item.children) > 1 else '')
    selected = next(
        (module.url for module in reversed(modules) if module.active), None
    )
    return item.model_copy(
        update={
            'children': [
                module.model_copy(update={'active': module.url == selected})
                for module in modules
            ],
        }
    )


@public
@typechecked
def build_navigation(
    pages: list[Page],
    current: Page,
    inventory: dict[str, ApiSymbol],
    config: Config | None = None,
) -> list[NavigationItem]:
    """
    title: Resolve the sidebar and keep API modules in stable accordions.
    parameters:
      pages:
        type: list[Page]
      current:
        type: Page
      inventory:
        type: dict[str, ApiSymbol]
      config:
        type: Config | None
    returns:
      type: list[NavigationItem]
    """
    automatic = automatic_navigation(pages, current, inventory)
    navigation = (
        configured_sidebar(config, automatic, pages, current, inventory)
        if config is not None
        else automatic
    )
    return [module_navigation(item) for item in navigation]


@private
@typechecked
def local_target(path: str, pages: list[Page]) -> tuple[Page, str]:
    """
    title: Resolve a docs-root page path and optional heading without guessing.
    parameters:
      path:
        type: str
      pages:
        type: list[Page]
    returns:
      type: tuple[Page, str]
    """
    try:
        target = urlsplit(path)
    except ValueError as error:
        raise BuildError('navigation', f'Invalid page path: {path}') from error
    route = unquote(target.path)
    if (
        target.scheme
        or target.netloc
        or route.startswith('/')
        or '..' in route.split('/')
        or not route
    ):
        raise BuildError('navigation', f'Invalid page path: {path}')
    if route.endswith(('.md', '.ipynb')):
        route = posixpath.splitext(route)[0] + '.html'
    if route.endswith('/'):
        route += 'index.html'
    page = next((page for page in pages if page.route == route), None)
    if page is None:
        raise BuildError('navigation', f'Unknown page: {path}')
    if target.fragment and unquote(target.fragment) not in page.anchors:
        raise BuildError('navigation', f'Unknown heading: {path}')
    suffix = f'?{target.query}' if target.query else ''
    suffix += f'#{target.fragment}' if target.fragment else ''
    return page, suffix


@private
@typechecked
def configured_items(
    entries: list[NavEntry],
    automatic: list[NavigationItem],
    pages: list[Page],
    current: Page,
    inventory: dict[str, ApiSymbol],
    expand_api: bool = True,
) -> list[NavigationItem]:
    """
    title: Resolve menu entries against planned routes and API sources.
    parameters:
      entries:
        type: list[NavEntry]
      automatic:
        type: list[NavigationItem]
      pages:
        type: list[Page]
      current:
        type: Page
      inventory:
        type: dict[str, ApiSymbol]
      expand_api:
        type: bool
    returns:
      type: list[NavigationItem]
    """
    result: list[NavigationItem] = []
    for entry in entries:
        children = configured_items(
            entry.children, automatic, pages, current, inventory, expand_api
        )
        item = NavigationItem(
            title=entry.title,
            url=None,
            current=False,
            active=any(child.active for child in children),
            children=children,
        )
        if entry.path is not None:
            page, suffix = local_target(entry.path, pages)
            item = navigation_item(page, current, children).model_copy(
                update={'title': entry.title}
            )
            section = posixpath.dirname(page.route)
            item = item.model_copy(
                update={
                    'url': str(item.url) + suffix,
                    'active': item.active
                    or (
                        bool(section)
                        and page.route.endswith('/index.html')
                        and current.route.startswith(section + '/')
                    ),
                }
            )
        elif entry.url is not None:
            try:
                target = urlsplit(entry.url)
            except ValueError as error:
                raise BuildError(
                    'navigation', f'Invalid URL: {entry.url}'
                ) from error
            if (
                target.scheme not in {'https', 'http', 'mailto'}
                or (target.scheme != 'mailto' and not target.netloc)
                or (not target.path and target.scheme == 'mailto')
            ):
                raise BuildError('navigation', f'Invalid URL: {entry.url}')
            item = item.model_copy(update={'url': entry.url})
        elif entry.api is not None:
            api_page = next(
                (
                    p
                    for p in pages
                    if p.route == 'api/index.html' and p.source is None
                ),
                None,
            )
            if api_page is None:
                raise BuildError('navigation', 'API pages are not generated')
            tree = next(
                item
                for item in automatic
                if item.url == navigation_item(api_page, current, []).url
            )
            children = tree.children
            if entry.api != '*':
                roots = {
                    navigation_item(page, current, []).url
                    for page in pages
                    if page.symbol is not None
                    and inventory[page.symbol].source_name == entry.api
                    and inventory[page.symbol].parent not in inventory
                }
                children = [child for child in children if child.url in roots]
                if not children:
                    raise BuildError(
                        'navigation', f'No API pages for source: {entry.api}'
                    )
                # A scoped menu links directly to its single package root.
                url = children[0].url if len(children) == 1 else None
                item = item.model_copy(
                    update={
                        'url': url,
                        'children': children,
                        'active': any(child.active for child in children),
                    }
                )
            else:
                item = tree.model_copy(update={'title': entry.title})
            item = item.model_copy(update={'layout': 'modules'})
            if not expand_api:
                # Header menus expose entry points; the full tree belongs
                # to the sidebar. Preserve a chooser for multiple roots.
                item = item.model_copy(
                    update={
                        'children': []
                        if item.url is not None
                        else [
                            child.model_copy(update={'children': []})
                            for child in item.children
                        ],
                        'current': item.url
                        == navigation_item(current, current, []).url,
                    }
                )
        result.append(item)
    return result


@private
@typechecked
def configured_sidebar(
    config: Config,
    automatic: list[NavigationItem],
    pages: list[Page],
    current: Page,
    inventory: dict[str, ApiSymbol],
) -> list[NavigationItem]:
    """
    title: Select one menu by front matter, longest route prefix, or default.
    parameters:
      config:
        type: Config
      automatic:
        type: list[NavigationItem]
      pages:
        type: list[Page]
      current:
        type: Page
      inventory:
        type: dict[str, ApiSymbol]
    returns:
      type: list[NavigationItem]
    """
    resolved = {
        sidebar.id: configured_items(
            sidebar.items, automatic, pages, current, inventory
        )
        for sidebar in config.navigation.sidebars
    }
    selected = sidebar_for_page(config, current)
    if (
        current.settings.sidebar is False
        or current.settings.layout == 'landing'
    ):
        return []
    if selected is not None:
        return resolved[selected.id]
    return automatic if not config.navigation.sidebars else []


@public
@typechecked
def sidebar_for_page(config: Config, current: Page) -> SidebarSettings | None:
    """
    title: Validate menu selection and expose the selected sidebar metadata.
    parameters:
      config:
        type: Config
      current:
        type: Page
    returns:
      type: SidebarSettings | None
    """
    settings = config.navigation
    sidebars: dict[str, SidebarSettings] = {}
    matches: list[tuple[int, str]] = []
    for sidebar in settings.sidebars:
        if sidebar.id in sidebars:
            raise BuildError('navigation', f'Duplicate sidebar: {sidebar.id}')
        sidebars[sidebar.id] = sidebar
        for prefix in sidebar.paths:
            if (
                not prefix
                or prefix.startswith('/')
                or '..' in prefix.split('/')
                or (not prefix.endswith('/') and not prefix.endswith('.html'))
            ):
                raise BuildError(
                    'navigation', f'Use a route prefix or HTML path: {prefix}'
                )
            if (
                current.route.startswith(prefix)
                if prefix.endswith('/')
                else current.route == prefix
            ):
                matches.append((len(prefix), sidebar.id))
    if settings.default_sidebar is not None and (
        settings.default_sidebar not in sidebars
    ):
        raise BuildError('navigation', 'Unknown default sidebar')
    choice = current.settings.sidebar
    if isinstance(choice, str):
        if choice not in sidebars:
            raise BuildError(
                'navigation', f'Unknown sidebar: {choice}', current.source
            )
        return sidebars[choice]
    if choice is False or current.settings.layout == 'landing':
        return None
    if matches:
        longest = max(length for length, _ in matches)
        selected = {name for length, name in matches if length == longest}
        if len(selected) != 1:
            raise BuildError(
                'navigation', f'Ambiguous sidebar for {current.route}'
            )
        return sidebars[selected.pop()]
    return sidebars.get(settings.default_sidebar or '')


@public
@typechecked
def build_navbar(
    config: Config,
    pages: list[Page],
    current: Page,
    inventory: dict[str, ApiSymbol],
) -> list[NavigationItem]:
    """
    title: Resolve ordered top-level menus using the same checked page routes.
    parameters:
      config:
        type: Config
      pages:
        type: list[Page]
      current:
        type: Page
      inventory:
        type: dict[str, ApiSymbol]
    returns:
      type: list[NavigationItem]
    """
    return configured_items(
        config.navigation.navbar,
        automatic_navigation(pages, current, inventory),
        pages,
        current,
        inventory,
        expand_api=False,
    )
