"""
title: Native API blocks and references in a CommonMark document.
"""

from __future__ import annotations

import json
import posixpath
import re

from html import escape
from pathlib import Path
from typing import Literal, Mapping

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
from doukimd.indexes import ApiIndex, api_index
from doukimd.models import ApiSymbol, Page, Settings
from doukimd.references import resolve_symbol
from doukimd.runtime import typechecked


@private
class ApiOptions(Settings):
    """
    title: Supported options for an API block.
    attributes:
      members:
        description: Whether to include public declaration members.
      show_source:
        description: Whether to display the source path and declaration line.
      source:
        description: Source content or configured API source name.
    """

    members: Literal['none', 'public'] = 'none'
    show_source: bool = True
    source: str | None = None


@private
@typechecked
def api_block(state: StateBlock, start: int, end: int, silent: bool) -> bool:
    """
    title: Parse API directives only at Markdown block boundaries.
    parameters:
      state:
        description: Current Markdown parser state.
      start:
        description: First document line to inspect.
      end:
        description: Exclusive final document line to inspect.
      silent:
        description: Whether to check syntax without emitting tokens.
    returns:
      description: Whether a valid API block was recognized.
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
        description: Current Markdown parser state.
      silent:
        description: Whether to check syntax without emitting tokens.
    returns:
      description: Whether an inline API reference was recognized.
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
      description: Parser configured with the supported Markdown dialect.
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
        description: Input value to validate or render.
    returns:
      description: Markdown representation of the structured field.
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
        description: Declaration or navigation entry being rendered.
      show_source:
        description: Whether to display the source path and declaration line.
    returns:
      description: Markdown for the declaration and its callable variants.
    """
    fence = '`' * max(
        3,
        1
        + max(
            (len(run) for run in re.findall(r'`+', item.signature)),
            default=0,
        ),
    )
    parts = [f'## {md_text(item.name)}']
    if item.signature and not item.variants:
        parts.append(f'{fence}python\n{item.signature}\n{fence}')
    if item.generated:
        parts.append('Generated from the class declaration.')
    for index, variant in enumerate(item.variants, start=1):
        parts.append(f'### Variant {index}')
        parts.append(f'{fence}python\n{variant.signature}\n{fence}')
        parts.append(documentation_markdown(variant.documentation))
    if show_source:
        parts.append(f'Source: {md_text(item.source)}:{item.line or 1}')
        if item.canonical and item.canonical != item.identifier:
            parts.append(f'Declared as: {md_text(item.canonical)}')
    if not item.variants:
        parts.append(documentation_markdown(item.documentation))
    return '\n\n'.join(parts)


@private
@typechecked
def documentation_markdown(data: Mapping[str, object]) -> str:
    """
    title: Format validated fields for one declaration or variant.
    parameters:
      data:
        description: Structured content or template data to process.
    returns:
      description: Markdown preserving validated documentation.
    """
    parts: list[str] = []
    for name, value in data.items():
        if name in {'title', 'summary'}:
            parts.append(describe(value))
        else:
            parts.append(f'### {name.replace("_", " ").title()}')
            if name in {'parameters', 'attributes'} and isinstance(
                value, dict
            ):
                parts.extend(
                    f'- **{md_text(str(key))}** — '
                    + field_description(field).replace('\n', '\n  ')
                    for key, field in value.items()
                )
            elif name in {'returns', 'yields'}:
                parts.append(field_description(value))
            else:
                parts.append(describe(value))
    return '\n\n'.join(parts)


@private
@typechecked
def field_description(value: object) -> str:
    """
    title: Format Douki types, defaults, and prose without JSON wrappers.
    parameters:
      value:
        description: Input value to validate or render.
    returns:
      description: Readable field types, defaults, and descriptions.
    """
    if not isinstance(value, dict):
        return describe(value)
    parts: list[str] = []
    for name, item in value.items():
        if name == 'type':
            parts.append(f'**Type:** {md_text(str(item))}')
        elif name == 'default':
            parts.append(f'**Default:** {md_text(str(item))}')
        elif name == 'description':
            parts.append(describe(item))
        else:
            parts.append(f'**{md_text(str(name))}:** {describe(item)}')
    return '; '.join(parts)


@public
@typechecked
def parse_document(
    parser: MarkdownIt,
    text: str,
    page: Page,
    inventory: ApiIndex | dict[str, ApiSymbol],
) -> list[Token]:
    """
    title: Expand API nodes into ordinary document tokens before resolution.
    parameters:
      parser:
        description: Parser used to process the document content.
      text:
        description: Text content to process.
      page:
        description: Page being compiled or used to resolve links.
      inventory:
        description: Collected API declarations keyed by symbol identity.
    returns:
      description: Parsed document tokens with API blocks expanded.
    """
    api = api_index(inventory)
    try:
        tokens = parser.parse(text)
        expanded: list[Token] = []
        for token in tokens:
            if token.type != 'doukimd_api':
                expanded.append(token)
                continue
            identifier = resolve_symbol(
                str(token.meta['identifier']),
                token.meta.get('source') or page.settings.api_source,
                api,
            )
            selected = [api.symbols[identifier]]
            if token.meta['members'] == 'public':
                selected.extend(api.children.get(identifier, ()))
            for item in selected:
                content = api_markdown(item, bool(token.meta['show_source']))
                # Authored HTML settings do not apply to docstrings.
                authored_html = parser.options['html']
                parser.options['html'] = False
                try:
                    children = parser.parse(content)
                finally:
                    parser.options['html'] = authored_html
                if any(t.type == 'doukimd_api' for t in children):
                    raise BuildError(
                        'douki',
                        'API directives cannot occur inside docstrings',
                    )
                heading = children[1]
                badge = Token('html_inline', '', 0)
                kind = escape(item.kind)
                badge.content = (
                    f'<span class="api-kind api-kind--{kind}">{kind}</span> '
                )
                heading.children = [badge, *(heading.children or [])]
                if page.symbol == item.identifier:
                    children[0].tag = 'h1'
                    children[2].tag = 'h1'
                for child in children:
                    for inline in child.children or []:
                        if inline.type == 'doukimd_ref':
                            inline.meta['source'] = item.source_name
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
        description: Parsed document tokens in rendering order.
      page:
        description: Page being compiled or used to resolve links.
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
    inventory: ApiIndex | dict[str, ApiSymbol],
    routes: ApiIndex | dict[str, str],
) -> None:
    """
    title: Resolve forward API references using the complete site inventory.
    parameters:
      tokens:
        description: Parsed document tokens in rendering order.
      page:
        description: Page being compiled or used to resolve links.
      inventory:
        description: Collected API declarations keyed by symbol identity.
      routes:
        description: Planned output routes used to validate destinations.
    """
    api = api_index(inventory)
    planned = routes.routes if isinstance(routes, ApiIndex) else routes
    for token in tokens:
        if token.children is None:
            continue
        children: list[Token] = []
        for child in token.children:
            if child.type != 'doukimd_ref':
                children.append(child)
                continue
            try:
                identifier = resolve_symbol(
                    str(child.meta['identifier']),
                    child.meta.get('source') or page.settings.api_source,
                    api,
                )
            except BuildError as error:
                raise BuildError(
                    'references',
                    f'No generated API page: {error.message}',
                    page.source,
                ) from error
            if identifier not in planned:
                raise BuildError(
                    'references',
                    f'No generated API page for {identifier}',
                    page.source,
                )
            link = Token('link_open', 'a', 1)
            link.attrSet(
                'href',
                posixpath.relpath(
                    planned[identifier], posixpath.dirname(page.route) or '.'
                ),
            )
            label = Token('text', '', 0)
            label.content = api.symbols[identifier].name
            children.extend([link, label, Token('link_close', 'a', -1)])
        token.children = children
