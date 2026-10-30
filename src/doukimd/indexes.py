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
    title: >-
      Validate symbol and route collections once and index their relations.
    summary: Copies prevent callers from replacing entries after validation.
    attributes:
      symbols:
        type: Mapping[str, ApiSymbol]
      routes:
        type: Mapping[str, str]
      children:
        type: Mapping[str | None, tuple[ApiSymbol, Ellipsis]]
      roots:
        type: Mapping[str | None, tuple[str, Ellipsis]]
      exact_names:
        type: Mapping[tuple[str | None, str], tuple[str, Ellipsis]]
      canonical_names:
        type: Mapping[tuple[str | None, str], tuple[str, Ellipsis]]
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
        title: >-
          Capture checked inputs independently of their mutable containers.
        parameters:
          symbols:
            type: dict[str, ApiSymbol]
          routes:
            type: dict[str, str] | None
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
            type: str
        returns:
          type: tuple[ApiSymbol, Ellipsis]
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
    title: >-
      Snapshot planned page membership while anchors are populated in place.
    attributes:
      pages:
        type: tuple[Page, Ellipsis]
      by_route:
        type: Mapping[str, Page]
      by_symbol:
        type: Mapping[str, Page]
      api_page:
        type: Page | None
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
            type: list[Page]
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
        type: ApiIndex | dict[str, ApiSymbol]
    returns:
      type: ApiIndex
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
        type: SiteIndex | list[Page]
    returns:
      type: SiteIndex
    """
    return pages if isinstance(pages, SiteIndex) else SiteIndex(pages)
