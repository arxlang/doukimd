"""
title: Validated immutable snapshots for one compilation.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from public import private

from doukimd.errors import BuildError
from doukimd.models import ApiSymbol, Page
from doukimd.runtime import typechecked


@private
@typechecked
@dataclass(frozen=True, init=False)
class ApiIndex:
    """
    title: Validate symbol and route collections once and index their
      relations.
    summary: Copies prevent callers from replacing entries after
      validation.
    attributes:
      symbols:
        description: API declarations keyed by stable identity.
      routes:
        description: Planned output routes used to validate destinations.
      children:
        description: Immediate children in display order.
      roots:
        description: Top-level entries in the selected hierarchy.
      exact_names:
        description: Symbols indexed by their fully qualified public
          names.
      canonical_names:
        description: Symbols indexed by their original declaration
          names.
    """

    symbols: Mapping[str, ApiSymbol]
    routes: Mapping[str, str]
    children: Mapping[str | None, tuple[ApiSymbol, ...]]
    roots: Mapping[str | None, tuple[str, ...]]
    exact_names: Mapping[tuple[str | None, str], tuple[str, ...]]
    canonical_names: Mapping[tuple[str | None, str], tuple[str, ...]]

    def __init__(
        self,
        symbols: dict[str, ApiSymbol],
        routes: dict[str, str] | None = None,
    ) -> None:
        """
        title: Capture checked inputs independently of their mutable
          containers.
        parameters:
          symbols:
            description: API declarations keyed by stable identity.
          routes:
            description: Planned output routes used to validate destinations.
        """
        captured = dict(symbols)
        children: dict[str | None, list[ApiSymbol]] = {}
        roots: dict[str | None, list[str]] = {}
        exact: dict[tuple[str | None, str], list[str]] = {}
        canonical: dict[tuple[str | None, str], list[str]] = {}
        for name, item in captured.items():
            children.setdefault(item.parent, []).append(item)
            for source in {None, item.source_name}:
                key = (source, name.rsplit(':', 1)[-1])
                exact.setdefault(key, []).append(name)
                if item.canonical is not None:
                    key = (source, item.canonical.rsplit(':', 1)[-1])
                    canonical.setdefault(key, []).append(name)
                if item.parent not in captured:
                    roots.setdefault(source, []).append(name)
        object.__setattr__(self, 'symbols', MappingProxyType(captured))
        object.__setattr__(
            self, 'routes', MappingProxyType(dict(routes or {}))
        )
        object.__setattr__(
            self,
            'children',
            MappingProxyType(
                {key: tuple(value) for key, value in children.items()}
            ),
        )
        object.__setattr__(
            self,
            'roots',
            MappingProxyType(
                {key: tuple(value) for key, value in roots.items()}
            ),
        )
        object.__setattr__(
            self,
            'exact_names',
            MappingProxyType(
                {key: tuple(value) for key, value in exact.items()}
            ),
        )
        object.__setattr__(
            self,
            'canonical_names',
            MappingProxyType(
                {key: tuple(value) for key, value in canonical.items()}
            ),
        )

    def ancestors(self, identifier: str) -> tuple[ApiSymbol, ...]:
        """
        title: Follow one symbol's ancestry without traversing unrelated APIs.
        parameters:
          identifier:
            description: Stable, source-qualified API identity.
        returns:
          description: Ancestor identities for the requested declaration.
        """
        result: list[ApiSymbol] = []
        seen: set[str] = set()
        while identifier in self.symbols:
            if identifier in seen:
                raise BuildError('api', f'Cyclic API parent: {identifier}')
            seen.add(identifier)
            item = self.symbols[identifier]
            result.append(item)
            if item.parent is None:
                break
            identifier = item.parent
        return tuple(result)


@private
@typechecked
@dataclass(frozen=True, init=False)
class SiteIndex:
    """
    title: Snapshot planned page membership while anchors are populated in
      place.
    attributes:
      pages:
        description: Pages with their planned output routes.
      by_route:
        description: Pages indexed by output route.
      by_symbol:
        description: Generated pages indexed by API identity.
      api_page:
        description: Generated page associated with the requested API symbol.
    """

    pages: tuple[Page, ...]
    by_route: Mapping[str, Page]
    by_symbol: Mapping[str, Page]
    api_page: Page | None

    def __init__(self, pages: list[Page]) -> None:
        """
        title: Capture checked pages after route planning has completed.
        parameters:
          pages:
            description: Pages with their planned output routes.
        """
        captured = tuple(pages)
        object.__setattr__(self, 'pages', captured)
        object.__setattr__(
            self,
            'by_route',
            MappingProxyType({page.route: page for page in captured}),
        )
        object.__setattr__(
            self,
            'by_symbol',
            MappingProxyType(
                {
                    page.symbol: page
                    for page in captured
                    if page.symbol is not None
                }
            ),
        )
        object.__setattr__(
            self,
            'api_page',
            next(
                (
                    page
                    for page in captured
                    if page.route == 'api/index.html' and page.source is None
                ),
                None,
            ),
        )


@private
@typechecked
def api_index(inventory: ApiIndex | dict[str, ApiSymbol]) -> ApiIndex:
    """
    title: Reuse a snapshot or validate a standalone helper's dictionary input.
    parameters:
      inventory:
        description: Collected API declarations keyed by symbol identity.
    returns:
      description: Validated API index shared by subsequent lookups.
    """
    return (
        inventory if isinstance(inventory, ApiIndex) else ApiIndex(inventory)
    )


@private
@typechecked
def site_index(pages: SiteIndex | list[Page]) -> SiteIndex:
    """
    title: Reuse a snapshot or validate a standalone helper's page list.
    parameters:
      pages:
        description: Pages with their planned output routes.
    returns:
      description: Validated site index shared by subsequent lookups.
    """
    return pages if isinstance(pages, SiteIndex) else SiteIndex(pages)
