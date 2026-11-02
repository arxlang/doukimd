"""
title: Bundle frontend assets and syntax colors without network requests.
"""

from __future__ import annotations

import json

from collections import OrderedDict
from importlib.resources import files
from typing import Callable, cast
from uuid import uuid4

from jinja2.runtime import Macro
from markupsafe import Markup
from public import private, public
from pygments.formatters import HtmlFormatter

from doukimd.models import ThemeSettings
from doukimd.navigation_plan import NavigationView
from doukimd.runtime import typechecked


@private
@typechecked
class NavigationFragments:
    """
    title: Cache bundled menu markup separately from page selection attributes.
    attributes:
      fragments:
        type: OrderedDict[tuple[int, int, str, bool], tuple[str, Ellipsis]]
      slots:
        type: >-
          dict[tuple[int, int, str, bool], tuple[tuple[int, bool], Ellipsis]]
    """

    def __init__(self) -> None:
        """
        title: Start with empty build-local bounded fragment caches.
        """
        self.fragments: OrderedDict[
            tuple[int, int, str, bool], tuple[str, ...]
        ] = OrderedDict()
        self.slots: dict[
            tuple[int, int, str, bool], tuple[tuple[int, bool], ...]
        ] = {}

    def render(
        self,
        macro: Macro,
        item: NavigationView,
        group_id: str,
        opened: bool,
    ) -> str:
        """
        title: Fill selection slots without rerendering escaped links.
        parameters:
          macro:
            type: Macro
          item:
            type: NavigationView
          group_id:
            type: str
          opened:
            type: bool
        returns:
          type: str
        """
        key = (id(item.node), id(item.selection.urls), group_id, opened)
        if key not in self.fragments:
            marker = f'__doukimd_{uuid4().hex}__'
            slots: list[tuple[int, bool]] = []

            @typechecked
            def attribute(view: NavigationView, location: bool) -> str:
                """
                title: Register an attribute slot without embedding page state.
                parameters:
                  view:
                    type: NavigationView
                  location:
                    type: bool
                returns:
                  type: str
                """
                slots.append((view.node.identifier, location))
                return marker

            self.fragments[key] = tuple(
                macro(item, group_id, opened, attribute).split(marker)
            )
            self.slots[key] = tuple(slots)
            if len(self.fragments) > 2048:
                removed, _ = self.fragments.popitem(last=False)
                del self.slots[removed]
        self.fragments.move_to_end(key)
        chunks = self.fragments[key]
        parts = [chunks[0]]
        current = item.selection.current
        active = item.selection.active
        for chunk, (identifier, location) in zip(chunks[1:], self.slots[key]):
            if identifier in current:
                parts.append(' aria-current="page"')
            elif location and identifier in active:
                parts.append(' aria-current="location"')
            parts.append(chunk)
        # Each chunk was escaped by Jinja; inserted attributes are literals.
        return Markup(''.join(parts))


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
