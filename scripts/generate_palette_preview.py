"""
title: Generate the documentation swatch chart from the actual theme presets.
"""

from __future__ import annotations

import xml.etree.ElementTree as xml

from pathlib import Path

from public import private

from doukimd.runtime import typechecked
from doukimd.theme import palette_colors

SVG = 'http://www.w3.org/2000/svg'
ROLES = {
    'bg': 'Canvas',
    'surface': 'Surface',
    'border': 'Border',
    'accent-soft': 'Highlight',
    'accent': 'Accent',
    'active': 'Active text',
    'code': 'Code',
    'muted': 'Muted text',
    'text': 'Body text',
}


@private
@typechecked
def element(
    parent: xml.Element,
    tag: str,
    attributes: dict[str, str],
    text: str | None = None,
) -> xml.Element:
    """
    title: Append a namespaced SVG element with safely escaped text.
    parameters:
      parent:
        type: xml.Element
      tag:
        type: str
      attributes:
        type: dict[str, str]
      text:
        type: str | None
    returns:
      type: xml.Element
    """
    node = xml.SubElement(parent, f'{{{SVG}}}{tag}', attributes)
    node.text = text
    return node


@private
@typechecked
def readable_ink(color: str) -> str:
    """
    title: Choose black or white for the highest swatch-label contrast.
    parameters:
      color:
        type: str
    returns:
      type: str
    """
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    luminance = sum(
        value * weight
        for value, weight in zip(linear, (0.2126, 0.7152, 0.0722))
    )
    return '#000000' if luminance > 0.179 else '#ffffff'


@private
@typechecked
def swatches(
    parent: xml.Element, colors: dict[str, str], x: float, y: float
) -> None:
    """
    title: Draw every semantic color with a role label and its exact hex value.
    parameters:
      parent:
        type: xml.Element
      colors:
        type: dict[str, str]
      x:
        type: float
      y:
        type: float
    """
    if set(colors) != set(ROLES):
        raise ValueError('Update the chart to cover all palette color roles')
    width = 156.0
    for index, (token, label) in enumerate(ROLES.items()):
        left = x + (index % 3) * (width + 7)
        top = y + (index // 3) * 67
        color = colors[token]
        ink = readable_ink(color)
        group = element(parent, 'g', {})
        element(group, 'title', {}, f'{label}: {color.upper()}')
        element(
            group,
            'rect',
            {
                'x': str(left),
                'y': str(top),
                'width': str(width),
                'height': '60',
                'rx': '8',
                'fill': color,
                'stroke': '#64748b',
                'stroke-opacity': '.18',
            },
        )
        element(
            group,
            'text',
            {
                'x': str(left + 13),
                'y': str(top + 24),
                'fill': ink,
                'font-size': '17',
                'font-weight': '600',
            },
            label,
        )
        element(
            group,
            'text',
            {
                'x': str(left + 13),
                'y': str(top + 46),
                'fill': ink,
                'font-size': '15',
                'font-family': 'DejaVu Sans Mono, monospace',
            },
            color.upper(),
        )


@private
@typechecked
def generate_preview(target: Path) -> None:
    """
    title: Save a responsive, accessible SVG without raster or network deps.
    parameters:
      target:
        type: Path
    """
    palettes = palette_colors()
    height = 132 + len(palettes) * 298 + (len(palettes) - 1) * 20 + 40
    xml.register_namespace('', SVG)
    root = xml.Element(
        f'{{{SVG}}}svg',
        {
            'viewBox': f'0 0 1120 {height}',
            'width': '1120',
            'height': str(height),
            'role': 'img',
            'aria-labelledby': 'chart-title chart-description',
            'font-family': 'DejaVu Sans, sans-serif',
        },
    )
    element(root, 'title', {'id': 'chart-title'}, 'DoukiMD color palettes')
    element(
        root,
        'desc',
        {'id': 'chart-description'},
        'Terracotta, Ocean, Forest, Violet, and Slate. Each card shows '
        'light and dark swatches for every theme color role, with hex '
        'values taken directly from the palette configuration.',
    )
    element(
        root,
        'rect',
        {
            'width': '1120',
            'height': str(height),
            'rx': '20',
            'fill': '#f3f5f8',
        },
    )
    element(
        root,
        'text',
        {
            'x': '40',
            'y': '59',
            'fill': '#243044',
            'font-size': '36',
            'font-weight': '700',
        },
        'Color palettes',
    )
    element(
        root,
        'text',
        {
            'x': '40',
            'y': '93',
            'fill': '#536174',
            'font-size': '18',
        },
        'Five presets. Light and dark. Every color, from the theme itself.',
    )
    for index, (name, modes) in enumerate(palettes.items()):
        top = 132 + index * 318
        card = element(root, 'g', {'aria-label': name.title()})
        element(
            card,
            'rect',
            {
                'x': '40',
                'y': str(top),
                'width': '1040',
                'height': '298',
                'rx': '16',
                'fill': '#ffffff',
                'stroke': '#e1e6ed',
            },
        )
        element(
            card,
            'circle',
            {
                'cx': '70',
                'cy': str(top + 31),
                'r': '7',
                'fill': modes['light']['accent'],
            },
        )
        element(
            card,
            'text',
            {
                'x': '89',
                'y': str(top + 39),
                'fill': '#243044',
                'font-size': '25',
                'font-weight': '700',
            },
            name.title(),
        )
        if name == 'terracotta':
            element(
                card,
                'text',
                {
                    'x': '260',
                    'y': str(top + 37),
                    'fill': '#667085',
                    'font-size': '15',
                },
                'DEFAULT',
            )
        for mode, left in [('light', 64.0), ('dark', 574.0)]:
            element(
                card,
                'text',
                {
                    'x': str(left),
                    'y': str(top + 72),
                    'fill': '#536174',
                    'font-size': '14',
                    'font-weight': '700',
                    'letter-spacing': '1',
                },
                mode.upper(),
            )
            swatches(card, modes[mode], left, float(top + 85))
    xml.indent(root, space='  ')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        xml.tostring(root, encoding='unicode') + '\n', encoding='utf-8'
    )


if __name__ == '__main__':
    generate_preview(
        Path(__file__).resolve().parents[1] / 'docs/assets/color-palettes.svg'
    )
