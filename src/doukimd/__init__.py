"""
title: DoukiMD, Markdown documentation powered by Douki.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from public import public

from doukimd.runtime import typechecked


@public
@typechecked
def get_version() -> str:
    """
    title: Return the installed version or the source-tree fallback.
    returns:
      type: str
    """
    try:
        return version('doukimd')
    except PackageNotFoundError:
        return '0.1.0'  # semantic-release


__version__ = get_version()
