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
      description: Installed package version or the source fallback.
    """
    try:
        return version('doukimd')
    except PackageNotFoundError:
        return '1.4.5'  # semantic-release


__version__ = get_version()
