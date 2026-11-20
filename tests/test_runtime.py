"""
title: Runtime checks and shared annotation metadata for dispatch wrappers.
"""

from __future__ import annotations

import inspect

from pathlib import Path

import pytest

from plum import Dispatcher
from typeguard import TypeCheckError

from doukimd.runtime import typechecked


@typechecked
def test_wrapper_shares_annotations_with_original() -> None:
    """
    title: Keep annotation resolution visible through the wrapper chain.
    """

    def echo(paths: list[Path]) -> list[Path]:
        """
        title: Return typed collection items unchanged.
        parameters:
          paths:
            description: Paths selected for processing.
        returns:
          description: The supplied collection unchanged.
        """
        return paths

    checked = typechecked(echo)
    assert checked.__annotations__ is echo.__annotations__
    assert inspect.unwrap(checked) is echo
    assert checked.__name__ == echo.__name__
    assert checked.__doc__ == echo.__doc__
    checked.__annotations__['paths'] = list[Path]
    parameter = inspect.signature(checked).parameters['paths']
    assert parameter.annotation == list[Path]
    assert checked([Path('guide.md')]) == [Path('guide.md')]
    with pytest.raises(TypeCheckError):
        checked([Path('guide.md'), 'invalid'])  # type: ignore[list-item]


@typechecked
def test_dispatch_resolves_wrapped_postponed_annotations() -> None:
    """
    title: Dispatch on resolved types and keep keyword argument validation.
    """
    dispatch = Dispatcher()

    @dispatch
    @typechecked
    def classify(value: object, *, suffix: str = '.html') -> str:
        """
        title: Reject unsupported values through the dispatch fallback.
        parameters:
          value:
            description: Input value to validate or render.
          suffix:
            default: .html
            description: Suffix appended to the generated route or fixture
              content.
        returns:
          description: Classification for a supported input value.
        """
        raise TypeError('Unsupported value')

    @typechecked
    def classify_path(value: Path, *, suffix: str = '.html') -> str:
        """
        title: Classify a path with a typed keyword argument.
        parameters:
          value:
            description: Input value to validate or render.
          suffix:
            default: .html
            description: Suffix appended to the generated route or fixture
              content.
        returns:
          description: Classification of the supplied path.
        """
        return value.name + suffix

    classify.dispatch(classify_path)
    assert classify(Path('guide.md')) == 'guide.md.html'
    assert classify(Path('guide.md'), suffix='!') == 'guide.md!'
    with pytest.raises(TypeError, match='Unsupported value'):
        classify(42)
    with pytest.raises(TypeCheckError):
        classify(Path('guide.md'), suffix=42)
