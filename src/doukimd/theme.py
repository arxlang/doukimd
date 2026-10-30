"""
title: Bundle frontend assets and syntax colors without network requests.
"""

from __future__ import annotations

import json

from importlib.resources import files
from typing import Callable, cast

from public import private, public
from pygments.formatters import HtmlFormatter

from doukimd.models import ThemeSettings
from doukimd.runtime import typechecked


@public
@typechecked
def palette_colors() -> dict[str, dict[str, dict[str, str]]]:
    """
    title: Read the bundled light and dark semantic color presets.
    returns:
      type: dict[str, dict[str, dict[str, str]]]
    """
    return cast(
        dict[str, dict[str, dict[str, str]]],
        json.loads(
            files('doukimd')
            .joinpath('themes/default/palettes.json')
            .read_text(encoding='utf-8')
        ),
    )


@private
@typechecked
def palette_styles() -> str:
    """
    title: Emit independent palette and appearance selectors with defaults.
    returns:
      type: str
    """
    rules = ['/* Radix Colors 3.0.0 (MIT): _doukimd/radix/LICENSE */']
    for name, modes in palette_colors().items():
        for mode, tokens in modes.items():
            selector = f'[data-palette="{name}"][data-bs-theme="{mode}"]'
            if name == 'terracotta':
                default = (
                    ':root'
                    if mode == 'light'
                    else ':root[data-bs-theme="dark"]'
                )
                selector = f'{default}, {selector}'
            colors = '\n'.join(
                f'  --dm-{token}: {color};' for token, color in tokens.items()
            )
            rules.append(f'{selector} {{\n{colors}\n}}')
    return '\n'.join(rules)


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
    stylesheet += ('\n' + palette_styles()).encode('utf-8')
    for mode, style in [('light', 'friendly'), ('dark', 'native')]:
        formatter = HtmlFormatter(style=style)
        rules = cast(Callable[[str], str], formatter.get_style_defs)(
            f'[data-bs-theme="{mode}"] .highlight'
        )
        stylesheet += ('\n' + rules).encode('utf-8')
    assets = {
        'theme.css': stylesheet,
        'theme.js': resources.joinpath('default/theme.js').read_bytes(),
        'search.js': resources.joinpath('default/search.js').read_bytes(),
        '_doukimd/radix/LICENSE': resources.joinpath(
            'vendor/radix/LICENSE'
        ).read_bytes(),
    }
    if settings.framework == 'bootstrap':
        for name in ['bootstrap.min.css', 'LICENSE']:
            assets[f'_doukimd/bootstrap/{name}'] = resources.joinpath(
                f'vendor/bootstrap/{name}'
            ).read_bytes()
    return assets
