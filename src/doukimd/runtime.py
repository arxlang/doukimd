"""
title: Runtime type checking for all arguments and collection items.
"""

from __future__ import annotations

import inspect

from functools import wraps
from typing import Callable, TypeVar, cast, get_type_hints

from public import public
from typeguard import CollectionCheckStrategy, check_type

T = TypeVar('T', bound=Callable[..., object])


@public
def typechecked(function: T) -> T:
    """
    title: Check package boundaries without changing global Typeguard settings.
    parameters:
      function:
        type: T
    returns:
      type: T
    """
    if isinstance(function, type):
        for name, member in list(vars(function).items()):
            if (
                inspect.isfunction(member)
                and member.__module__ == function.__module__
            ):
                setattr(function, name, typechecked(member))
        return function

    signature = inspect.signature(function)
    annotations: dict[str, object] | None = None

    @wraps(function)
    def checked(*args: object, **kwargs: object) -> object:
        """
        title: Validate all bound arguments and the return value.
        parameters:
          args:
            type: object
            variadic: positional
          kwargs:
            type: object
            variadic: keyword
        returns:
          type: object
        """
        nonlocal annotations
        if annotations is None:
            annotations = get_type_hints(function)
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        for name, value in bound.arguments.items():
            if name not in annotations:
                continue
            kind = signature.parameters[name].kind
            values = (
                value
                if kind == inspect.Parameter.VAR_POSITIONAL
                else cast(dict[str, object], value).values()
                if kind == inspect.Parameter.VAR_KEYWORD
                else (value,)
            )
            for item in cast(tuple[object, ...], values):
                check_type(
                    item,
                    annotations[name],
                    collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS,
                )
        result = function(*args, **kwargs)
        if 'return' in annotations:
            check_type(
                result,
                annotations['return'],
                collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS,
            )
        return result

    return cast(T, checked)
