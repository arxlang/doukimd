"""
title: Build deterministic search records from expanded document content.
"""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import quote

from markdown_it.token import Token
from public import private, public

from doukimd.models import Page
from doukimd.runtime import typechecked


@private
@typechecked
class TextContent(HTMLParser):
    """
    title: Extract visible text without indexing scripts or styles.
    attributes:
      parts:
        type: list[str]
      hidden:
        type: list[str]
    """

    def __init__(self) -> None:
        """
        title: Initialize a reader for a single HTML fragment.
        """
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        """
        title: Skip scripts and styles while retaining image labels.
        parameters:
          tag:
            type: str
          attrs:
            type: list[tuple[str, str | None]]
        """
        if tag in {'script', 'style'}:
            self.hidden.append(tag)
        if not self.hidden:
            self.parts.append(' ')
            if tag == 'img':
                self.parts.extend(
                    value
                    for name, value in attrs
                    if name == 'alt' and value is not None
                )

    def handle_endtag(self, tag: str) -> None:
        """
        title: Resume visible text after ignored markup.
        parameters:
          tag:
            type: str
        """
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()
        if not self.hidden:
            self.parts.append(' ')

    def handle_data(self, data: str) -> None:
        """
        title: Collect text only when it is visible document content.
        parameters:
          data:
            type: str
        """
        if not self.hidden:
            self.parts.append(data)


@private
@typechecked
def html_text(value: str) -> str:
    """
    title: Normalize visible HTML into plain search text.
    parameters:
      value:
        type: str
    returns:
      type: str
    """
    parser = TextContent()
    parser.feed(value)
    parser.close()
    return ' '.join(''.join(parser.parts).split())


@private
@typechecked
def document_text(tokens: list[Token]) -> str:
    """
    title: Index prose, code, literal outputs, and rich output fallback text.
    parameters:
      tokens:
        type: list[Token]
    returns:
      type: str
    """
    reader = TextContent()
    for token in tokens:
        if token.type in {'fence', 'code_block'}:
            reader.handle_data(' ' + token.content + ' ')
        if token.type == 'html_block':
            reader.feed(token.content)
        for child in token.children or []:
            if child.type in {'text', 'code_inline', 'image'}:
                reader.handle_data(' ' + child.content + ' ')
            elif child.type == 'html_inline':
                reader.feed(child.content)
        rich = token.meta.get('search_text')
        if isinstance(rich, str):
            reader.handle_data(' ' + rich + ' ')
    reader.close()
    return ' '.join(''.join(reader.parts).split())


@public
@typechecked
def search_records(page: Page, tokens: list[Token]) -> list[dict[str, str]]:
    """
    title: Emit a page record plus independently linkable Markdown sections.
    parameters:
      page:
        type: Page
      tokens:
        type: list[Token]
    returns:
      type: list[dict[str, str]]
    """
    if not page.settings.search:
        return []
    url = quote(page.route)
    title = page.symbol.removeprefix('python:') if page.symbol else page.title
    records = [{'title': title, 'url': url, 'text': document_text(tokens)}]
    headings = [
        index
        for index, token in enumerate(tokens)
        if token.type == 'heading_open' and token.tag in {'h2', 'h3'}
    ]
    for position, start in enumerate(headings):
        end = (
            headings[position + 1]
            if position + 1 < len(headings)
            else len(tokens)
        )
        heading = document_text([tokens[start + 1]])
        records.append(
            {
                'title': f'{title} · {heading}',
                'url': url + '#' + quote(str(tokens[start].attrGet('id'))),
                'text': document_text(tokens[start:end]),
            }
        )
    return records
