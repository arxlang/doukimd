"""
title: Resolve API references within explicitly selected source folders.
"""

from __future__ import annotations

from public import public

from doukimd.errors import BuildError
from doukimd.models import ApiSymbol
from doukimd.runtime import typechecked


@public
@typechecked
def resolve_symbol(
    reference: str, source: str | None, inventory: dict[str, ApiSymbol]
) -> str:
    """
    title: Resolve exact or source-relative names and reject ambiguity.
    parameters:
      reference:
        type: str
      source:
        type: str | None
      inventory:
        type: dict[str, ApiSymbol]
    returns:
      type: str
    """
    if reference.count(':') >= 2:
        if reference not in inventory:
            raise BuildError('api', f'Unknown API symbol: {reference}')
        return reference
    path = reference.removeprefix('python:')
    candidates = [
        name
        for name, item in inventory.items()
        if (source is None or item.source_name == source)
        and (
            name.split(':')[-1] == path
            or (
                item.canonical is not None
                and item.canonical.split(':')[-1] == path
            )
        )
    ]
    exact = [name for name in candidates if name.split(':')[-1] == path]
    matches = exact or candidates
    if len(matches) != 1:
        message = 'Ambiguous' if matches else 'Unknown'
        raise BuildError(
            'api', f'{message} API symbol: {reference}; source={source}'
        )
    return matches[0]
