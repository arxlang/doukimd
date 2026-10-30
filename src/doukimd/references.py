"""
title: Resolve API references within explicitly selected source folders.
"""

from __future__ import annotations

from public import public

from doukimd.errors import BuildError
from doukimd.indexes import ApiIndex, api_index
from doukimd.models import ApiSymbol
from doukimd.runtime import typechecked


@public
@typechecked
def resolve_symbol(
    reference: str,
    source: str | None,
    inventory: ApiIndex | dict[str, ApiSymbol],
) -> str:
    """
    title: Resolve exact or source-relative names and reject ambiguity.
    parameters:
      reference:
        type: str
      source:
        type: str | None
      inventory:
        type: ApiIndex | dict[str, ApiSymbol]
    returns:
      type: str
    """
    api = api_index(inventory)
    if reference.count(':') >= 2:
        if reference not in api.symbols:
            raise BuildError('api', f'Unknown API symbol: {reference}')
        return reference
    path = reference.removeprefix('python:')
    key = (source, path)
    matches = api.exact_names.get(key) or api.canonical_names.get(key, ())
    if len(matches) != 1:
        message = 'Ambiguous' if matches else 'Unknown'
        raise BuildError(
            'api', f'{message} API symbol: {reference}; source={source}'
        )
    return matches[0]
