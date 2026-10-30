"""
title: Validate links and anchors in explicitly enabled authored HTML.
"""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser
from typing import Callable

from markdown_it.token import Token
from public import private, public

from doukimd.errors import BuildError
from doukimd.models import Page
from doukimd.runtime import typechecked


@private
@typechecked
class HtmlContent(HTMLParser):
    """
    title: Preserve trusted HTML while resolving local links or gathering ids.
    attributes:
      page:
        type: Page
      resolve:
        type: Callable[[str], str] | None
      parts:
        type: list[str]
    """

    def __init__(
        self, page: Page, resolve: Callable[[str], str] | None
    ) -> None:
        """
        title: Initialize a token-local HTML reader.
        parameters:
          page:
            type: Page
          resolve:
            type: Callable[[str], str] | None
        """
        super().__init__(convert_charrefs=False)
        self.page: Page = page
        self.resolve: Callable[[str], str] | None = resolve
        self.parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        """
        title: Collect explicit anchors or rewrite URL-bearing attributes.
        parameters:
          tag:
            type: str
          attrs:
            type: list[tuple[str, str | None]]
        """
        rendered: list[str] = []
        for name, value in attrs:
            if name == 'id' and value is not None and self.resolve is None:
                if value in self.page.anchors:
                    raise BuildError(
                        'references',
                        f'Duplicate HTML id: {value}',
                        self.page.source,
                    )
                self.page.anchors.add(value)
            if (
                self.resolve is not None
                and value is not None
                and name in {'href', 'src', 'poster'}
            ):
                value = self.resolve(value)
            rendered.append(
                name
                if value is None
                else f'{name}="{escape(value, quote=True)}"'
            )
        attributes = (' ' + ' '.join(rendered)) if rendered else ''
        self.parts.append(f'<{tag}{attributes}>')

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        """
        title: Preserve self-closing markup after attribute resolution.
        parameters:
          tag:
            type: str
          attrs:
            type: list[tuple[str, str | None]]
        """
        self.handle_starttag(tag, attrs)
        self.parts[-1] = self.parts[-1][:-1] + ' />'

    def handle_endtag(self, tag: str) -> None:
        """
        title: Retain closing tags.
        parameters:
          tag:
            type: str
        """
        self.parts.append(f'</{tag}>')

    def handle_data(self, data: str) -> None:
        """
        title: Retain literal text including script and style bodies.
        parameters:
          data:
            type: str
        """
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        """
        title: Retain named character references.
        parameters:
          name:
            type: str
        """
        self.parts.append(f'&{name};')

    def handle_charref(self, name: str) -> None:
        """
        title: Retain numeric character references.
        parameters:
          name:
            type: str
        """
        self.parts.append(f'&#{name};')

    def handle_comment(self, data: str) -> None:
        """
        title: Preserve authored comments.
        parameters:
          data:
            type: str
        """
        self.parts.append(f'<!--{data}-->')

    def handle_decl(self, decl: str) -> None:
        """
        title: Preserve declarations.
        parameters:
          decl:
            type: str
        """
        self.parts.append(f'<!{decl}>')

    def handle_pi(self, data: str) -> None:
        """
        title: Preserve processing instructions.
        parameters:
          data:
            type: str
        """
        self.parts.append(f'<?{data}>')


@public
@typechecked
def process_html(
    tokens: list[Token],
    page: Page,
    resolve: Callable[[str], str] | None = None,
) -> None:
    """
    title: Gather raw anchors before Markdown anchors, then resolve HTML URLs.
    parameters:
      tokens:
        type: list[Token]
      page:
        type: Page
      resolve:
        type: Callable[[str], str] | None
    """
    if not page.settings.html:
        return
    for token in tokens:
        for item in [token, *(token.children or [])]:
            if item.meta.get('notebook_output'):
                continue
            if item.type not in {'html_block', 'html_inline'}:
                continue
            parser = HtmlContent(page, resolve)
            parser.feed(item.content)
            parser.close()
            if resolve is not None:
                item.content = ''.join(parser.parts)
