"""
title: Copy explicitly selected documentation assets without source escapes.
"""

from __future__ import annotations

import posixpath

from pathlib import Path
from urllib.parse import quote

from public import public

from doukimd.config import project_path
from doukimd.errors import BuildError
from doukimd.models import Config
from doukimd.runtime import typechecked


@public
@typechecked
def copy_assets(root: Path, config: Config) -> dict[str, bytes]:
    """
    title: Copy matched docs-relative files and reject unsafe patterns.
    parameters:
      root:
        description: Project root used to resolve relative paths.
      config:
        description: Validated project settings or their configuration file.
    returns:
      description: Output destinations mapped to their asset bytes.
    """
    docs = project_path(root, config.docs_dir)
    result: dict[str, bytes] = {}
    for pattern in config.assets:
        if (
            not pattern
            or Path(pattern).is_absolute()
            or '..' in Path(pattern).parts
            or '\\' in pattern
        ):
            raise BuildError('assets', f'Invalid asset pattern: {pattern}')
        # pathlib glob does not recurse through linked directories. Check
        # their containment too, so an escape is never silently omitted.
        for path in docs.rglob('*'):
            if path.is_symlink() and not path.resolve().is_relative_to(docs):
                raise BuildError(
                    'assets', 'Asset escapes docs directory', path
                )
        matches: list[Path] = []
        for path in docs.glob(pattern):
            matches.extend(path.rglob('*') if path.is_dir() else [path])
        files = [path for path in matches if path.is_file()]
        if not files and pattern != 'assets/**':
            raise BuildError('assets', f'No assets match: {pattern}')
        for path in sorted(files):
            if not path.resolve().is_relative_to(docs):
                raise BuildError(
                    'assets', 'Asset escapes docs directory', path
                )
            if path.suffix.lower() in {'.md', '.ipynb'}:
                raise BuildError(
                    'assets', 'Asset pattern selects source', path
                )
            result[path.relative_to(docs).as_posix()] = path.read_bytes()
    return result


@public
@typechecked
def asset_url(
    value: str | None, route: str, assets: dict[str, bytes]
) -> str | None:
    """
    title: Resolve a configured docs-root asset relative to a planned page.
    parameters:
      value:
        description: Input value to validate or render.
      route:
        description: Planned output path relative to the site root.
      assets:
        description: Asset destinations and bytes included in the build.
    returns:
      description: Validated asset link relative to the current page.
    """
    if value is None:
        return None
    if value not in assets:
        raise BuildError('assets', f'Asset is not copied: {value}')
    return quote(posixpath.relpath(value, posixpath.dirname(route) or '.'))
