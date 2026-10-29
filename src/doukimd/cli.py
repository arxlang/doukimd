"""
title: Build and validate DoukiMD projects from the command line.
"""

from __future__ import annotations

from pathlib import Path

import click

from public import public

from doukimd import get_version
from doukimd.build import build_site, compile_site
from doukimd.errors import BuildError
from doukimd.runtime import typechecked


@click.group()
@click.version_option(version=get_version())
@public
@typechecked
def main() -> None:
    """
    title: Build Markdown documentation and Douki API references.
    """


@main.command()
@click.option(
    '--config',
    'config_path',
    type=click.Path(path_type=Path),
    default=Path('doukimd.yaml'),
    show_default=True,
)
@public
@typechecked
def build(config_path: Path) -> None:
    """
    title: Build a static HTML documentation site.
    parameters:
      config_path:
        type: Path
    """
    try:
        result = build_site(config_path)
    except (BuildError, OSError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f'Built {result.page_count} pages.')


@main.command()
@click.option(
    '--config',
    'config_path',
    type=click.Path(path_type=Path),
    default=Path('doukimd.yaml'),
    show_default=True,
)
@public
@typechecked
def check(config_path: Path) -> None:
    """
    title: Validate a complete site without writing output.
    parameters:
      config_path:
        type: Path
    """
    try:
        result = compile_site(config_path)
    except (BuildError, OSError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f'Checked {result.page_count} pages.')
