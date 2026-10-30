"""
title: Expand notebook cells and saved MIME outputs into document tokens.
"""

from __future__ import annotations

import base64
import binascii
import json
import re

from dataclasses import replace
from html import escape
from pathlib import Path
from urllib.parse import unquote

from markdown_it import MarkdownIt
from markdown_it.token import Token
from plum import dispatch
from public import private, public

from doukimd.content import expand_page
from doukimd.errors import BuildError
from doukimd.indexes import ApiIndex
from doukimd.markdown import parse_document
from doukimd.models import ApiSymbol, Config, Page
from doukimd.notebook_models import (
    CodeCell,
    ErrorOutput,
    MarkdownCell,
    RawCell,
    RichOutput,
    StreamOutput,
)
from doukimd.notebooks import notebook_text
from doukimd.runtime import typechecked
from doukimd.search import html_text

IMAGES = {
    'image/svg+xml',
    'image/png',
    'image/jpeg',
    'image/gif',
    'image/webp',
}
PRIORITY = (
    'text/html',
    'image/svg+xml',
    'image/png',
    'image/jpeg',
    'image/gif',
    'image/webp',
    'text/markdown',
    'application/json',
    'text/plain',
)


@private
@typechecked
def mime_text(value: object) -> str:
    """
    title: Decode textual MIME values without coercing arbitrary JSON objects.
    parameters:
      value:
        type: object
    returns:
      type: str
    """
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(
        isinstance(item, str) for item in value
    ):
        return ''.join(str(item) for item in value)
    raise BuildError('notebook', 'Expected a string or string list MIME value')


@private
@typechecked
def image_url(mime: str, value: object) -> str:
    """
    title: Embed SVG only in image context and validate raster base64 data.
    parameters:
      mime:
        type: str
      value:
        type: object
    returns:
      type: str
    """
    text = mime_text(value)
    if mime == 'image/svg+xml':
        encoded = base64.b64encode(text.encode('utf-8')).decode('ascii')
    else:
        encoded = ''.join(text.split())
        try:
            base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as error:
            raise BuildError(
                'notebook', 'Invalid base64 image output'
            ) from error
    return f'data:{mime};base64,{encoded}'


@private
@typechecked
def output_token(content: str, text: str = '') -> Token:
    """
    title: Keep generated output markup separate from authored HTML processing.
    parameters:
      content:
        type: str
      text:
        type: str
    returns:
      type: Token
    """
    token = Token('html_block', '', 0)
    token.content = content + '\n'
    token.meta = {'notebook_output': True, 'search_text': text}
    return token


@private
@typechecked
def literal_output(text: str, kind: str = 'text') -> list[Token]:
    """
    title: Escape terminal text and remove nonportable ANSI escape sequences.
    parameters:
      text:
        type: str
      kind:
        type: str
    returns:
      type: list[Token]
    """
    text = re.sub(
        r'\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))', '', text
    )
    return [
        output_token(
            f'<pre class="notebook-output notebook-output--{kind}">'
            f'{escape(text)}</pre>',
            text,
        )
    ]


@private
@typechecked
class NotebookRenderer:
    """
    title: Visit supported cells and outputs with a fail-closed fallback.
    attributes:
      page:
        type: Page
      root:
        type: Path
      config:
        type: Config
      context:
        type: dict[str, object]
      parser:
        type: MarkdownIt
      inventory:
        type: ApiIndex | dict[str, ApiSymbol]
      language:
        type: str
      footnotes:
        type: int
    """

    def __init__(
        self,
        page: Page,
        root: Path,
        config: Config,
        context: dict[str, object],
        parser: MarkdownIt,
        inventory: ApiIndex | dict[str, ApiSymbol],
        language: str,
    ) -> None:
        """
        title: Share the page's normal expansion and reference pipeline.
        parameters:
          page:
            type: Page
          root:
            type: Path
          config:
            type: Config
          context:
            type: dict[str, object]
          parser:
            type: MarkdownIt
          inventory:
            type: ApiIndex | dict[str, ApiSymbol]
          language:
            type: str
        """
        self.page: Page = page
        self.root: Path = root
        self.config: Config = config
        self.context: dict[str, object] = context
        self.parser: MarkdownIt = parser
        self.inventory: ApiIndex | dict[str, ApiSymbol] = inventory
        self.language: str = language
        self.footnotes: int = 0

    @dispatch
    def visit(self, value: object) -> list[Token]:
        """
        title: Reject unknown cell and output models explicitly.
        parameters:
          value:
            type: object
        returns:
          type: list[Token]
        """
        raise BuildError(
            'notebook', f'Unsupported notebook node: {type(value)}'
        )

    @dispatch
    def visit(self, value: MarkdownCell) -> list[Token]:
        """
        title: Expand only Markdown sources with the existing page settings.
        parameters:
          value:
            type: MarkdownCell
        returns:
          type: list[Token]
        """
        page = replace(
            self.page, body=notebook_text(value.source), notebook=None
        )
        body = expand_page(page, self.root, self.config, self.context)
        tokens = parse_document(self.parser, body, self.page, self.inventory)
        maximum = -1
        for token in tokens:
            for item in [token, *(token.children or [])]:
                if item.type.startswith('footnote_') and 'id' in item.meta:
                    local = int(item.meta['id'])
                    maximum = max(maximum, local)
                    item.meta['id'] = local + self.footnotes
                    number = str(item.meta['id'] + 1)
                    if item.type == 'footnote_open':
                        self.page.anchors.add('fn' + number)
                    if item.type == 'footnote_ref':
                        sub = int(item.meta.get('subId', 0))
                        suffix = f':{sub}' if sub else ''
                        self.page.anchors.add('fnref' + number + suffix)
        self.footnotes += maximum + 1
        for token in tokens:
            for child in token.children or []:
                attribute = 'src' if child.type == 'image' else 'href'
                target = child.attrGet(attribute)
                if not isinstance(target, str) or not target.startswith(
                    'attachment:'
                ):
                    continue
                if child.type != 'image':
                    raise BuildError(
                        'notebook', 'Attachments require image links'
                    )
                name = unquote(target.removeprefix('attachment:'))
                bundle = value.attachments.get(name, {})
                mime = next(
                    (
                        mime
                        for mime in PRIORITY
                        if mime in IMAGES and mime in bundle
                    ),
                    None,
                )
                if mime is None:
                    raise BuildError(
                        'notebook', f'Unknown image attachment: {name}'
                    )
                child.attrSet('src', image_url(mime, bundle[mime]))
        return tokens

    @dispatch
    def visit(self, value: CodeCell) -> list[Token]:
        """
        title: Render literal inputs and saved outputs in order.
        parameters:
          value:
            type: CodeCell
        returns:
          type: list[Token]
        """
        tokens = [
            output_token('<div class="notebook-cell notebook-cell--code">')
        ]
        if 'remove-input' not in value.metadata.tags:
            count = (
                str(value.execution_count)
                if value.execution_count is not None
                else ' '
            )
            tokens.append(
                output_token(
                    f'<div class="notebook-prompt">In [{count}]</div>'
                )
            )
            code = Token('fence', 'code', 0)
            code.content = notebook_text(value.source)
            code.info = self.language
            tokens.append(code)
        if 'remove-output' not in value.metadata.tags:
            for output in value.outputs:
                tokens.extend(self.visit(output))
        tokens.append(output_token('</div>'))
        return tokens

    @dispatch
    def visit(self, value: RawCell) -> list[Token]:
        """
        title: Preserve raw cells as literal text without markup evaluation.
        parameters:
          value:
            type: RawCell
        returns:
          type: list[Token]
        """
        return literal_output(notebook_text(value.source), 'raw')

    @dispatch
    def visit(self, value: StreamOutput) -> list[Token]:
        """
        title: Preserve recorded stdout and stderr without interpretation.
        parameters:
          value:
            type: StreamOutput
        returns:
          type: list[Token]
        """
        return literal_output(notebook_text(value.text), value.name)

    @dispatch
    def visit(self, value: ErrorOutput) -> list[Token]:
        """
        title: Render a saved traceback or its recorded exception summary.
        parameters:
          value:
            type: ErrorOutput
        returns:
          type: list[Token]
        """
        text = '\n'.join(value.traceback) or f'{value.ename}: {value.evalue}'
        return literal_output(text, 'error')

    @dispatch
    def visit(self, value: RichOutput) -> list[Token]:
        """
        title: Select a static MIME alternative or reject the bundle.
        parameters:
          value:
            type: RichOutput
        returns:
          type: list[Token]
        """
        mime = next((mime for mime in PRIORITY if mime in value.data), None)
        if mime is None:
            raise BuildError(
                'notebook', f'No supported output MIME: {sorted(value.data)}'
            )
        data = value.data[mime]
        if mime in IMAGES:
            variant = ' notebook-image--svg' if mime == 'image/svg+xml' else ''
            return [
                output_token(
                    f'<figure class="notebook-image{variant}">'
                    '<img alt="Saved notebook output" '
                    f'src="{image_url(mime, data)}"></figure>',
                    html_text(mime_text(data))
                    if mime == 'image/svg+xml'
                    else mime_text(value.data.get('text/plain', '')),
                )
            ]
        if mime == 'application/json':
            return literal_output(
                json.dumps(data, ensure_ascii=False, indent=2)
            )
        text = mime_text(data)
        if mime == 'text/html':
            policy = (
                "default-src 'none'; style-src 'unsafe-inline'; "
                "img-src data:; base-uri 'none'; form-action 'none'"
            )
            document = (
                '<!doctype html><html><head><meta charset="utf-8">'
                '<meta http-equiv="Content-Security-Policy" '
                f'content="{policy}"><style>body{{font:14px system-ui;'
                'margin:12px;color:#222;background:#fff}table{'
                'border-collapse:collapse}td,th{padding:.4em .7em;'
                'border:1px solid #ccc}img,svg{max-width:100%}</style>'
                f'</head><body>{text}</body></html>'
            )
            return [
                output_token(
                    '<iframe class="notebook-rich-output" sandbox="" '
                    'referrerpolicy="no-referrer" title="Saved HTML output" '
                    f'srcdoc="{escape(document, quote=True)}"></iframe>',
                    html_text(text),
                )
            ]
        if mime == 'text/markdown':
            parser = MarkdownIt('commonmark', {'html': False}).enable('table')
            return parser.parse(text)
        return literal_output(text)


@public
@typechecked
def render_notebook(
    page: Page,
    root: Path,
    config: Config,
    context: dict[str, object],
    parser: MarkdownIt,
    inventory: ApiIndex | dict[str, ApiSymbol],
) -> list[Token]:
    """
    title: Expand saved notebook content before anchors and links are resolved.
    parameters:
      page:
        type: Page
      root:
        type: Path
      config:
        type: Config
      context:
        type: dict[str, object]
      parser:
        type: MarkdownIt
      inventory:
        type: ApiIndex | dict[str, ApiSymbol]
    returns:
      type: list[Token]
    """
    notebook = page.notebook
    if notebook is None:
        raise BuildError(
            'notebook', 'Notebook content is missing', page.source
        )
    info = notebook.metadata.get('language_info', {})
    kernel = notebook.metadata.get('kernelspec', {})
    language = str(info.get('name', '')) if isinstance(info, dict) else ''
    if not language and isinstance(kernel, dict):
        language = str(kernel.get('language', ''))
    renderer = NotebookRenderer(
        page, root, config, context, parser, inventory, language
    )
    tokens: list[Token] = []
    for index, cell in enumerate(notebook.cells, start=1):
        if 'remove-cell' in cell.metadata.tags:
            continue
        try:
            tokens.extend(renderer.visit(cell))
        except BuildError as error:
            raise BuildError(
                error.phase, f'Cell {index}: {error.message}', page.source
            ) from error
    return tokens
