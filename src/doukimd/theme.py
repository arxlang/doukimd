"""
title: Bundle frontend assets and syntax colors without network requests.
"""

from __future__ import annotations

from importlib.resources import files
from typing import Callable, cast

from public import public
from pygments.formatters import HtmlFormatter

from doukimd.models import ThemeSettings
from doukimd.runtime import typechecked


@public
@typechecked
def theme_assets(settings: ThemeSettings) -> dict[str, bytes]:
    """
    title: Select bundled framework assets and adaptive syntax highlighting.
    parameters:
      settings:
        type: ThemeSettings
    returns:
      type: dict[str, bytes]
    """
    resources = files('doukimd').joinpath('themes')
    stylesheet = resources.joinpath('default/theme.css').read_bytes()
    for mode, style in [('light', 'friendly'), ('dark', 'native')]:
        formatter = HtmlFormatter(style=style)
        rules = cast(Callable[[str], str], formatter.get_style_defs)(
            f'[data-bs-theme="{mode}"] .highlight'
        )
        stylesheet += ('\n' + rules).encode('utf-8')
    assets = {
        'theme.css': stylesheet,
        'theme.js': resources.joinpath('default/theme.js').read_bytes(),
    }
    if settings.framework == 'bootstrap':
        for name in ['bootstrap.min.css', 'LICENSE']:
            assets[f'_doukimd/bootstrap/{name}'] = resources.joinpath(
                f'vendor/bootstrap/{name}'
            ).read_bytes()
    return assets
