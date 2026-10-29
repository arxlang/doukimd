"""
title: Native API blocks and references in a CommonMark document.
"""

from __future__ import annotations

import json
import posixpath
import re

from pathlib import Path
from typing import Literal

from markdown_it import MarkdownIt
from markdown_it.rules_block import StateBlock
from markdown_it.rules_inline import StateInline
from markdown_it.token import Token
from mdit_py_plugins.footnote import footnote_plugin
from public import private, public
from pydantic import ValidationError

from doukimd.config import read_yaml
from doukimd.content import md_text
from doukimd.errors import BuildError
from doukimd.models import ApiSymbol, Page, Settings
from doukimd.runtime import typechecked


@private
class ApiOptions(Settings):
    """
    title: Supported options for an API block.
    attributes:
      members:
        type: Literal[none, public]
      show_source:
        type: bool
    """

    members: Literal['none', 'public'] = 'none'
    show_source: bool = True


@private
@typechecked
def api_block(state: StateBlock, start: int, end: int, silent: bool) -> bool:
    """
    title: Parse API directives only at Markdown block boundaries.
    parameters:
      state:
        type: StateBlock
      start:
        type: int
      end:
        type: int
      silent:
        type: bool
    returns:
      type: bool
    """
    if state.is_code_block(start):
        return False
    line = state.src[
        state.bMarks[start] + state.tShift[start] : state.eMarks[start]
    ]
    if not line.startswith('::: api '):
        return False
    if silent:
        return True
    identifier = line.removeprefix('::: api ').strip()
    close = start + 1
    while close < end:
        text = state.src[
            state.bMarks[close] + state.tShift[close] : state.eMarks[close]
        ]
        if text.strip() == ':::':
            break
        close += 1
    if close == end:
        raise BuildError('markdown', 'Unterminated API block')
    raw = state.getLines(start + 1, close, state.blkIndent, False)
    try:
        options = ApiOptions.model_validate(
            read_yaml(raw, Path('<api-block>')) if raw.strip() else {}
        )
    except ValidationError as error:
        raise BuildError('markdown', str(error)) from error
    token = state.push('doukimd_api', '', 0)
    token.meta = {'identifier': identifier, **options.model_dump()}
    token.map = [start, close + 1]
    state.line = close + 1
    return True


@private
@typechecked
def api_reference(state: StateInline, silent: bool) -> bool:
    """
    title: Preserve inline API references as structured tokens.
    parameters:
      state:
        type: StateInline
      silent:
        type: bool
    returns:
      type: bool
    """
    match = re.match(r'\{@api\s+([^}\s]+)\}', state.src[state.pos :])
    if match is None:
        return False
    if not silent:
        token = state.push('doukimd_ref', '', 0)
        token.meta = {'identifier': match[1]}
    state.pos += len(match[0])
    return True


@public
@typechecked
def markdown_parser() -> MarkdownIt:
    """
    title: Construct the supported Markdown dialect.
    returns:
      type: MarkdownIt
    """
    parser = MarkdownIt('commonmark', {'html': False})
    parser.enable('table')
    parser.use(footnote_plugin)
    parser.block.ruler.before(
        'fence', 'doukimd_api', api_block, {'alt': ['paragraph']}
    )
    parser.inline.ruler.before('text', 'doukimd_ref', api_reference)
    return parser


@private
@typechecked
def describe(value: object) -> str:
    """
    title: Preserve structured Douki fields in readable Markdown.
    parameters:
      value:
        type: object
    returns:
      type: str
    """
    if isinstance(value, str):
        return value
    if value is None:
        return ''
    if isinstance(value, list):
        return '\n\n'.join(describe(item) for item in value)
    if isinstance(value, dict):
        chunks: list[str] = []
        for name, item in value.items():
            if name == 'description':
                chunks.append(describe(item))
            elif name == 'code' and isinstance(item, str):
                fence = '`' * max(
                    3,
                    1
                    + max(
                        (len(run) for run in re.findall(r'`+', item)),
                        default=0,
                    ),
                )
                chunks.append(f'{fence}python\n{item}\n{fence}')
            elif isinstance(item, (dict, list)):
                chunks.append(f'### {md_text(name)}\n\n{describe(item)}')
            else:
                encoded = json.dumps(item, ensure_ascii=False)
                chunks.append(f'- **{md_text(name)}:** {md_text(encoded)}')
        return '\n\n'.join(chunks)
    return str(value)


@private
@typechecked
def api_markdown(item: ApiSymbol, show_source: bool) -> str:
    """
    title: Expand a validated symbol without evaluating its prose as Jinja.
    parameters:
      item:
        type: ApiSymbol
      show_source:
        type: bool
    returns:
      type: str
    """
    fence = '`' * max(
        3,
        1
        + max(
            (len(run) for run in re.findall(r'`+', item.signature)),
            default=0,
        ),
    )
    parts = [
        f'## {md_text(item.name)}',
        f'{fence}python\n{item.signature}\n{fence}',
    ]
    if show_source:
        parts.append(f'Source: {md_text(item.source)}:{item.line or 1}')
    for name, value in item.documentation.items():
        if name in {'title', 'summary'}:
            parts.append(describe(value))
        else:
            parts.append(f'### {name.replace("_", " ").title()}')
            parts.append(describe(value))
    return '\n\n'.join(parts)


@public
@typechecked
def parse_document(
    parser: MarkdownIt, text: str, page: Page, inventory: dict[str, ApiSymbol]
) -> list[Token]:
    """
    title: Expand API nodes into ordinary document tokens before resolution.
    parameters:
      parser:
        type: MarkdownIt
      text:
        type: str
      page:
        type: Page
      inventory:
        type: dict[str, ApiSymbol]
    returns:
      type: list[Token]
    """
    try:
        tokens = parser.parse(text)
        if page.symbol is not None:
            marker = Token('doukimd_api', '', 0)
            marker.meta = {
                'identifier': page.symbol,
                'members': 'none',
                'show_source': True,
            }
            tokens = [marker]
        expanded: list[Token] = []
        for token in tokens:
            if token.type != 'doukimd_api':
                expanded.append(token)
                continue
            identifier = str(token.meta['identifier'])
            if identifier not in inventory:
                raise BuildError('api', f'Unknown API symbol: {identifier}')
            selected = [inventory[identifier]]
            if token.meta['members'] == 'public':
                selected.extend(
                    item
                    for item in inventory.values()
                    if item.parent == identifier
                )
            for item in selected:
                content = api_markdown(item, bool(token.meta['show_source']))
                children = parser.parse(content)
                if any(t.type == 'doukimd_api' for t in children):
                    raise BuildError(
                        'douki',
                        'API directives cannot occur inside docstrings',
                    )
                expanded.extend(children)
        return expanded
    except BuildError as error:
        raise BuildError(error.phase, error.message, page.source) from error


@public
@typechecked
def assign_anchors(tokens: list[Token], page: Page) -> None:
    """
    title: Assign deterministic unique heading anchors before link resolution.
    parameters:
      tokens:
        type: list[Token]
      page:
        type: Page
    """
    for index, token in enumerate(tokens):
        if token.type != 'heading_open':
            continue
        text = tokens[index + 1].content
        slug = re.sub(r'[^\w-]+', '-', text.lower()).strip('-') or 'section'
        anchor = slug
        suffix = 1
        while anchor in page.anchors:
            anchor = f'{slug}-{suffix}'
            suffix += 1
        token.attrSet('id', anchor)
        page.anchors.add(anchor)


@public
@typechecked
def resolve_references(
    tokens: list[Token],
    page: Page,
    inventory: dict[str, ApiSymbol],
    routes: dict[str, str],
) -> None:
    """
    title: Resolve forward API references using the complete site inventory.
    parameters:
      tokens:
        type: list[Token]
      page:
        type: Page
      inventory:
        type: dict[str, ApiSymbol]
      routes:
        type: dict[str, str]
    """
    for token in tokens:
        if token.children is None:
            continue
        children: list[Token] = []
        for child in token.children:
            if child.type != 'doukimd_ref':
                children.append(child)
                continue
            identifier = str(child.meta['identifier'])
            if identifier not in routes:
                raise BuildError(
                    'references',
                    f'No generated API page for {identifier}',
                    page.source,
                )
            link = Token('link_open', 'a', 1)
            link.attrSet(
                'href',
                posixpath.relpath(
                    routes[identifier], posixpath.dirname(page.route) or '.'
                ),
            )
            label = Token('text', '', 0)
            label.content = inventory[identifier].name
            children.extend([link, label, Token('link_close', 'a', -1)])
        token.children = children
