"""
title: Compile, validate, and safely publish a static documentation site.
"""

from __future__ import annotations

import json
import posixpath
import shutil

from importlib.resources import files
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Callable, cast
from urllib.parse import unquote, urlsplit

from jinja2 import (
    BaseLoader,
    ChoiceLoader,
    Environment,
    PackageLoader,
    StrictUndefined,
    TemplateError,
)
from markdown_it.token import Token
from public import private, public
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

from doukimd.api import collect_api
from doukimd.config import load_config, load_data, project_path
from doukimd.content import (
    ProjectLoader,
    discover_pages,
    expand_page,
    plan_pages,
)
from doukimd.errors import BuildError
from doukimd.markdown import (
    assign_anchors,
    markdown_parser,
    parse_document,
    resolve_references,
)
from doukimd.models import Config, Page, SiteBuild
from doukimd.navigation import build_navigation
from doukimd.plugins import plugin_context
from doukimd.runtime import typechecked

MANIFEST = '.doukimd-manifest.json'


@private
@typechecked
def output_path(root: Path, config: Config) -> Path:
    """
    title: Reject output paths that overlap any project input.
    parameters:
      root:
        type: Path
      config:
        type: Config
    returns:
      type: Path
    """
    output = project_path(root, config.output_dir)
    protected = [
        root,
        project_path(root, config.docs_dir),
        project_path(root, config.includes_dir),
    ]
    protected.extend(
        project_path(root, source.root) for source in config.api.sources
    )
    protected.extend(
        project_path(root, value) for value in config.data.values()
    )
    if config.theme.directory is not None:
        protected.append(project_path(root, config.theme.directory))
    for source in protected:
        if source == root:
            overlap = output == root
        else:
            overlap = output.is_relative_to(source) or source.is_relative_to(
                output
            )
        if overlap:
            raise BuildError('config', 'Output overlaps project input', output)
    if output.exists() and not output.is_dir():
        raise BuildError('output', 'Output is not a directory', output)
    if output.is_dir() and any(output.iterdir()):
        manifest = output / MANIFEST
        try:
            data = json.loads(manifest.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, ValueError) as error:
            raise BuildError(
                'output', 'Refusing to replace an unmanaged directory', output
            ) from error
        if (
            not isinstance(data, dict)
            or data.get('generator') != 'doukimd'
            or data.get('schema_version') != 1
        ):
            raise BuildError('output', 'Invalid output manifest', manifest)
    return output


@private
@typechecked
def highlight_code(code: str, language: str, attrs: str) -> str:
    """
    title: Highlight code with a plain-text fallback for unknown languages.
    parameters:
      code:
        type: str
      language:
        type: str
      attrs:
        type: str
    returns:
      type: str
    """
    del attrs
    try:
        lexer = get_lexer_by_name(language) if language else TextLexer()
    except ClassNotFound:
        lexer = TextLexer()
    return highlight(code, lexer, HtmlFormatter())


@private
@typechecked
def copy_assets(root: Path, config: Config) -> dict[str, bytes]:
    """
    title: Read only assets from the dedicated documentation assets directory.
    parameters:
      root:
        type: Path
      config:
        type: Config
    returns:
      type: dict[str, bytes]
    """
    docs = project_path(root, config.docs_dir)
    assets = docs / 'assets'
    result: dict[str, bytes] = {}
    if assets.exists():
        for path in sorted(assets.rglob('*')):
            if not path.resolve().is_relative_to(docs):
                raise BuildError(
                    'assets', 'Asset escapes docs directory', path
                )
            if path.is_file():
                result[path.relative_to(docs).as_posix()] = path.read_bytes()
    return result


@private
@typechecked
def validate_links(
    tokens: list[Token],
    page: Page,
    pages: dict[str, Page],
    assets: dict[str, bytes],
) -> None:
    """
    title: Rewrite Markdown links and validate local files and anchors.
    parameters:
      tokens:
        type: list[Token]
      page:
        type: Page
      pages:
        type: dict[str, Page]
      assets:
        type: dict[str, bytes]
    """
    for token in tokens:
        for child in token.children or []:
            attribute = (
                'src'
                if child.type == 'image'
                else 'href'
                if child.type == 'link_open'
                else None
            )
            if attribute is None:
                continue
            value = child.attrGet(attribute)
            if value is None:
                continue
            if not isinstance(value, str):
                raise BuildError('references', 'Link target must be text')
            target = urlsplit(value)
            if target.scheme or target.netloc or value.startswith('/'):
                continue
            path = unquote(target.path)
            if path.endswith('.md'):
                path = path[:-3] + '.html'
            destination = path + 'index.html' if path.endswith('/') else path
            route = (
                posixpath.normpath(
                    posixpath.join(posixpath.dirname(page.route), destination)
                )
                if path
                else page.route
            )
            if route not in pages and route not in assets:
                raise BuildError(
                    'references', f'Unknown local target: {value}', page.source
                )
            if target.fragment and route in pages:
                if unquote(target.fragment) not in pages[route].anchors:
                    raise BuildError(
                        'references',
                        f'Unknown heading anchor: {value}',
                        page.source,
                    )
            child.attrSet(
                attribute,
                path
                + (f'?{target.query}' if target.query else '')
                + (f'#{target.fragment}' if target.fragment else ''),
            )


@public
@typechecked
def compile_site(config_path: Path) -> SiteBuild:
    """
    title: Compile all pages and references without writing output.
    parameters:
      config_path:
        type: Path
    returns:
      type: SiteBuild
    """
    config_path = config_path.resolve()
    root = config_path.parent
    config = load_config(config_path)
    output_path(root, config)
    inventory = collect_api(root, config)
    pages = discover_pages(root, config)
    routes = plan_pages(pages, inventory, config)
    if not pages:
        raise BuildError('planning', 'The site has no pages')
    context: dict[str, object] = {
        'site': config.site.model_dump(),
        'project': config.project.model_dump(),
        'data': load_data(root, config),
        'api': {
            name: {
                'name': item.name,
                'kind': item.kind,
                'signature': item.signature,
                'documentation': item.documentation,
                'source': item.source,
                'line': item.line,
            }
            for name, item in inventory.items()
        },
        'plugins': plugin_context(config),
        'build': {'format': 'html'},
    }
    parser = markdown_parser()
    parser.options['highlight'] = highlight_code
    documents: dict[str, list[Token]] = {}
    for page in pages:
        text = expand_page(page, root, config, context)
        tokens = parse_document(parser, text, page, inventory)
        assign_anchors(tokens, page)
        documents[page.route] = tokens
    assets = copy_assets(root, config)
    by_route = {page.route: page for page in pages}
    for page in pages:
        tokens = documents[page.route]
        resolve_references(tokens, page, inventory, routes)
        validate_links(tokens, page, by_route, assets)
    loaders: list[BaseLoader] = [PackageLoader('doukimd', 'themes/default')]
    if config.theme.directory is not None:
        custom = project_path(root, config.theme.directory)
        if not custom.is_dir():
            raise BuildError('theme', 'Theme directory is missing', custom)
        loaders.insert(0, ProjectLoader(custom))
    environment = Environment(
        loader=ChoiceLoader(loaders),
        undefined=StrictUndefined,
        autoescape=True,
    )
    artifacts = dict(assets)
    artifacts['theme.css'] = files('doukimd').joinpath(
        'themes/default/theme.css'
    ).read_bytes() + cast(
        Callable[[str], str], HtmlFormatter().get_style_defs
    )('.highlight').encode('utf-8')
    search: list[dict[str, str]] = []
    for page in pages:
        tokens = documents[page.route]
        content = parser.renderer.render(tokens, parser.options, {})
        relative = posixpath.dirname(page.route) or '.'
        nav = build_navigation(pages, page, inventory)
        toc = [
            {
                'title': ''.join(
                    child.content
                    for child in tokens[index + 1].children or []
                    if child.type in {'text', 'code_inline'}
                ),
                'url': '#' + str(token.attrGet('id')),
                'level': token.tag,
            }
            for index, token in enumerate(tokens)
            if token.type == 'heading_open' and token.tag in {'h2', 'h3'}
        ]
        try:
            html = environment.get_template('page.html').render(
                **context,
                page={
                    'title': page.title,
                    'url': page.route,
                    'meta': page.settings.meta,
                },
                content=content,
                navigation=nav,
                table_of_contents=toc,
                stylesheet=posixpath.relpath('theme.css', relative),
            )
        except TemplateError as error:
            raise BuildError('theme', str(error), page.source) from error
        if page.route in artifacts:
            raise BuildError('planning', f'Asset collides with {page.route}')
        artifacts[page.route] = html.encode('utf-8')
        search.append(
            {
                'title': page.title,
                'url': page.route,
                'text': ' '.join(
                    token.content for token in tokens if token.type == 'inline'
                ),
            }
        )
    artifacts['search.json'] = json.dumps(
        search, ensure_ascii=False, sort_keys=True
    ).encode('utf-8')
    artifacts['symbols.json'] = json.dumps(
        {
            'schema_version': 1,
            'symbols': {
                name: {
                    'url': routes.get(name),
                    'signature': item.signature,
                    'source': item.source,
                    'line': item.line,
                }
                for name, item in sorted(inventory.items())
            },
        },
        sort_keys=True,
    ).encode('utf-8')
    artifacts[MANIFEST] = json.dumps(
        {
            'schema_version': 1,
            'generator': 'doukimd',
            'files': sorted(artifacts),
        },
        sort_keys=True,
    ).encode('utf-8')
    return SiteBuild(artifacts, len(pages))


@public
@typechecked
def build_site(config_path: Path) -> SiteBuild:
    """
    title: Replace managed output only after the entire build succeeds.
    parameters:
      config_path:
        type: Path
    returns:
      type: SiteBuild
    """
    config_path = config_path.resolve()
    result = compile_site(config_path)
    config = load_config(config_path)
    output = output_path(config_path.parent, config)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(
        prefix='.doukimd-', dir=output.parent
    ) as temporary:
        staging = Path(temporary) / 'site'
        staging.mkdir()
        for route, content in result.files.items():
            target = staging.joinpath(*PurePosixPath(route).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        previous = Path(temporary) / 'previous'
        if output.exists():
            output.rename(previous)
        try:
            staging.rename(output)
        except OSError:
            if previous.exists():
                previous.rename(output)
            raise
        if previous.exists():
            shutil.rmtree(previous)
    return result
