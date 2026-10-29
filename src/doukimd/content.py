"""
title: Discover authored pages and expand their Markdown templates.
"""

from __future__ import annotations

import hashlib
import posixpath
import re

from collections import Counter
from pathlib import Path
from typing import Callable

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateError,
)
from jinja2.sandbox import ImmutableSandboxedEnvironment
from public import private, public
from pydantic import ValidationError

from doukimd.config import project_path, read_yaml
from doukimd.errors import BuildError
from doukimd.models import ApiSymbol, Config, Page, PageSettings
from doukimd.runtime import typechecked


@private
@typechecked
class ProjectLoader(FileSystemLoader):
    """
    title: Confine template files to a configured directory.
    attributes:
      directory:
        type: Path
    """

    directory: Path

    def __init__(self, directory: Path) -> None:
        """
        title: Initialize a loader rooted at a resolved directory.
        parameters:
          directory:
            type: Path
        """
        self.directory = directory.resolve()
        super().__init__(str(self.directory))

    def get_source(
        self, environment: Environment, template: str
    ) -> tuple[str, str, Callable[[], bool]]:
        """
        title: Check template containment before reading content.
        parameters:
          environment:
            type: Environment
          template:
            type: str
        returns:
          type: tuple[str, str, Callable[[], bool]]
        """
        project_path(self.directory, template)
        return super().get_source(environment, template)


@public
@typechecked
def split_front_matter(text: str, source: Path) -> tuple[PageSettings, str]:
    """
    title: Extract literal front matter before any template evaluation.
    parameters:
      text:
        type: str
      source:
        type: Path
    returns:
      type: tuple[PageSettings, str]
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != '---':
        return PageSettings(), text
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == '---':
            try:
                raw = ''.join(lines[1:index])
                settings = PageSettings.model_validate(
                    read_yaml(raw, source) if raw.strip() else {}
                )
            except ValidationError as error:
                raise BuildError('metadata', str(error), source) from error
            return settings, ''.join(lines[index + 1 :])
    raise BuildError('metadata', 'Unterminated front matter', source)


@public
@typechecked
def discover_pages(root: Path, config: Config) -> list[Page]:
    """
    title: Discover Markdown pages while preserving relative routes.
    parameters:
      root:
        type: Path
      config:
        type: Config
    returns:
      type: list[Page]
    """
    docs = project_path(root, config.docs_dir)
    if not docs.is_dir():
        raise BuildError(
            'discovery', 'Documentation directory is missing', docs
        )
    pages: list[Page] = []
    for path in sorted(docs.rglob('*.md')):
        if not path.resolve().is_relative_to(docs):
            raise BuildError('discovery', 'Page escapes docs directory', path)
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError) as error:
            raise BuildError('discovery', str(error), path) from error
        settings, body = split_front_matter(text, path)
        relative = path.relative_to(docs)
        route = relative.with_suffix('.html').as_posix()
        title = settings.title
        if title is None:
            heading = re.search(r'^# +(.+)$', body, flags=re.MULTILINE)
            title = heading[1] if heading else relative.stem
        pages.append(Page(route, title, body, settings, path))
    return pages


@public
@typechecked
def api_route(identifier: str) -> str:
    """
    title: Assign a stable route that does not depend on source traversal.
    parameters:
      identifier:
        type: str
    returns:
      type: str
    """
    language, path = identifier.split(':', maxsplit=1)
    return f'api/{language}/{path.replace(":", "/")}.html'


@private
@typechecked
def api_summary(
    items: list[ApiSymbol], route: str, routes: dict[str, str]
) -> str:
    """
    title: Group links to immediate API children by declaration kind.
    parameters:
      items:
        type: list[ApiSymbol]
      route:
        type: str
      routes:
        type: dict[str, str]
    returns:
      type: str
    """
    groups = [
        ('module', 'Modules'),
        ('class', 'Classes'),
        ('function', 'Functions'),
        ('method', 'Methods'),
        ('property', 'Properties'),
        ('attribute', 'Attributes'),
        ('enum-member', 'Enum values'),
        ('type-alias', 'Type aliases'),
    ]
    sections: list[str] = []
    for kind, title in groups:
        members = sorted(
            (item for item in items if item.kind == kind),
            key=lambda item: item.identifier,
        )
        if not members:
            continue
        sections.append(f'## {title}')
        for item in members:
            target = posixpath.relpath(
                routes[item.identifier], posixpath.dirname(route)
            )
            summary = ' '.join(
                str(item.documentation.get('title', '')).split()
            )
            label = (
                f'{item.source_name} / {item.name}'
                if route == 'api/index.html' and item.source_name
                else item.name
            )
            sections.append(
                f'- [{md_text(label)}]({target}) — {md_text(str(summary))}'
            )
    return '\n\n'.join(sections)


@public
@typechecked
def plan_pages(
    pages: list[Page], inventory: dict[str, ApiSymbol], config: Config
) -> dict[str, str]:
    """
    title: Add virtual API pages and reject duplicate routes.
    parameters:
      pages:
        type: list[Page]
      inventory:
        type: dict[str, ApiSymbol]
      config:
        type: Config
    returns:
      type: dict[str, str]
    """
    routes: dict[str, str] = {}
    if config.api.generate_pages and inventory:
        routes = {name: api_route(name) for name in inventory}
        counts = Counter(route.casefold() for route in routes.values())
        for name, route in list(routes.items()):
            if counts[route.casefold()] > 1:
                suffix = hashlib.sha256(name.encode('utf-8')).hexdigest()[:16]
                routes[name] = route[:-5] + f'--{suffix}.html'
        roots = [
            item for item in inventory.values() if item.parent not in inventory
        ]
        pages.append(
            Page(
                'api/index.html',
                'API Docs',
                api_summary(roots, 'api/index.html', routes),
                PageSettings(),
            )
        )
        for identifier, item in sorted(inventory.items()):
            route = routes[identifier]
            pages.append(
                Page(
                    route,
                    (
                        f'{item.source_name} / {item.name}'
                        if item.source_name and item.parent not in inventory
                        else item.name
                    ),
                    f'::: api {identifier}\n:::\n\n'
                    + api_summary(
                        [
                            child
                            for child in inventory.values()
                            if child.parent == identifier
                        ],
                        route,
                        routes,
                    ),
                    PageSettings(),
                    symbol=identifier,
                )
            )
    seen: set[str] = set()
    for page in pages:
        if page.route.casefold() in seen:
            raise BuildError('planning', f'Duplicate route: {page.route}')
        seen.add(page.route.casefold())
    return routes


@private
@typechecked
def md_text(value: str) -> str:
    """
    title: Escape plain text inserted into Markdown templates.
    parameters:
      value:
        type: str
    returns:
      type: str
    """
    return re.sub(r'([\\`*_{}\[\]()#+.!<>|~-])', r'\\\1', value)


@public
@typechecked
def expand_page(
    page: Page, root: Path, config: Config, context: dict[str, object]
) -> str:
    """
    title: Render enabled content templates exactly once.
    parameters:
      page:
        type: Page
      root:
        type: Path
      config:
        type: Config
      context:
        type: dict[str, object]
    returns:
      type: str
    """
    if page.settings.render != 'jinja':
        return page.body
    includes = project_path(root, config.includes_dir)
    environment = ImmutableSandboxedEnvironment(
        loader=ProjectLoader(includes),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )
    environment.filters['md_text'] = md_text
    try:
        return environment.from_string(page.body).render(
            **context,
            page={
                'title': page.title,
                'url': page.route,
                'meta': page.settings.meta,
                'api_source': page.settings.api_source,
            },
        )
    except TemplateError as error:
        raise BuildError(
            'template',
            f'{error}; locations refer to the Markdown template',
            page.source,
        ) from error
