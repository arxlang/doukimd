"""
title: Immutable build indexes and complete collection validation.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from typeguard import TypeCheckError

from doukimd.errors import BuildError
from doukimd.indexes import ApiIndex, SiteIndex
from doukimd.models import ApiSymbol, Page, PageSettings
from doukimd.references import resolve_symbol
from doukimd.runtime import typechecked


@typechecked
def symbol(
    identifier: str,
    parent: str | None = None,
    canonical: str | None = None,
) -> ApiSymbol:
    """
    title: Create a declaration with a stable named-source identity.
    parameters:
      identifier:
        type: str
      parent:
        type: str | None
      canonical:
        type: str | None
    returns:
      type: ApiSymbol
    """
    return ApiSymbol(
        identifier=identifier,
        name=identifier.rsplit('.', 1)[-1],
        kind='class',
        signature='',
        source='src/example.py',
        line=1,
        documentation={'title': 'Example.'},
        parent=parent,
        source_name=identifier.split(':')[1],
        canonical=canonical or identifier,
    )


@typechecked
def test_index_snapshots_and_validation() -> None:
    """
    title: Validate every input entry and prevent replacement after capture.
    """
    name = 'python:first:example.Widget'
    item = symbol(name)
    values = {name: item}
    routes = {name: 'api/widget.html'}
    api = ApiIndex(values, routes)
    values.clear()
    routes[name] = 'changed.html'
    assert api.symbols[name] is item
    assert api.routes[name] == 'api/widget.html'
    assert api.roots[None] == (name,)
    assert api.children[None] == (item,)
    with pytest.raises(TypeError):
        api.symbols[name] = item  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        api.symbols = {}  # type: ignore[misc]
    with pytest.raises(TypeCheckError):
        ApiIndex({name: item, 'last': object()})  # type: ignore[dict-item]
    with pytest.raises(TypeCheckError):
        ApiIndex({name: item}, {name: 'ok', 'last': 42})  # type: ignore[dict-item]
    page = Page('index.html', 'Home', '', PageSettings())
    pages = [page]
    site = SiteIndex(pages)
    pages.clear()
    page.anchors.add('later')
    assert site.pages == (page,)
    assert 'later' in site.by_route['index.html'].anchors
    with pytest.raises(TypeCheckError):
        SiteIndex([page, 'last'])  # type: ignore[list-item]


@typechecked
def test_indexed_symbol_resolution() -> None:
    """
    title: Preserve exact names, source isolation, and ambiguity errors.
    """
    original = 'python:first:example.Widget'
    alias = 'python:first:example.Exported'
    other = 'python:second:example.Widget'
    api = ApiIndex(
        {
            original: symbol(original),
            alias: symbol(alias, canonical=original),
            other: symbol(other),
        }
    )
    assert resolve_symbol('example.Widget', 'first', api) == original
    assert resolve_symbol(alias, None, api) == alias
    assert resolve_symbol('example.Exported', None, api) == alias
    with pytest.raises(BuildError, match='Ambiguous'):
        resolve_symbol('example.Widget', None, api)
    with pytest.raises(BuildError, match='Unknown'):
        resolve_symbol('missing', 'first', api)
    with pytest.raises(BuildError, match='Unknown'):
        resolve_symbol('python:first:missing', None, api)


@typechecked
def test_index_rejects_cyclic_parent_walk() -> None:
    """
    title: Fail closed when a malformed inventory contains cyclic parents.
    """
    first = 'python:first:example.A'
    second = 'python:first:example.B'
    api = ApiIndex(
        {
            first: symbol(first, second),
            second: symbol(second, first),
        }
    )
    with pytest.raises(BuildError, match='Cyclic API parent'):
        api.ancestors(first)
