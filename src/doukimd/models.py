"""
title: Validated configuration and build models.
"""

from __future__ import annotations

from dataclasses import field
from pathlib import Path
from typing import Literal

from public import public
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from pydantic.dataclasses import dataclass

from doukimd.notebook_models import Notebook
from doukimd.runtime import typechecked


@public
class Settings(BaseModel):
    """
    title: Reject unknown settings and implicit value coercion.
    """

    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)


@public
class SiteSettings(Settings):
    """
    title: Site presentation settings.
    attributes:
      title:
        type: str
      base_url:
        type: str
      description:
        type: str
      logo:
        type: str | None
      logo_alt:
        type: str
      favicon:
        type: str | None
    """

    title: str
    base_url: str = ''
    description: str = ''
    logo: str | None = None
    logo_alt: str = ''
    favicon: str | None = None


@public
class ProjectSettings(Settings):
    """
    title: Project metadata available to content templates.
    attributes:
      name:
        type: str
      version:
        type: str
    """

    name: str
    version: str = ''


@public
class PythonSource(Settings):
    """
    title: Configure static collection of explicitly selected Python modules.
    attributes:
      language:
        type: Literal[python]
      name:
        type: str | None
      root:
        type: str
      modules:
        type: list[str]
    """

    language: Literal['python'] = 'python'
    name: str | None = Field(default=None, pattern=r'^[a-zA-Z][\w-]*$')
    root: str = 'src'
    modules: list[str] = Field(default_factory=list)


@public
class ApiSettings(Settings):
    """
    title: API source discovery and virtual reference pages.
    attributes:
      sources:
        type: list[PythonSource]
      generate_pages:
        type: bool
    """

    sources: list[PythonSource] = Field(default_factory=list)
    generate_pages: bool = True


@public
class ThemeSettings(Settings):
    """
    title: Frontend framework, color preference, and local template overrides.
    attributes:
      stylesheets:
        type: list[str]
      directory:
        type: str | None
      framework:
        type: Literal[bootstrap, none]
      color_mode:
        type: Literal[auto, light, dark]
      palette:
        type: Literal[terracotta, ocean, forest, violet, slate]
    """

    stylesheets: list[str] = Field(default_factory=list)
    directory: str | None = None
    framework: Literal['bootstrap', 'none'] = 'bootstrap'
    color_mode: Literal['auto', 'light', 'dark'] = 'auto'
    palette: Literal['terracotta', 'ocean', 'forest', 'violet', 'slate'] = (
        'terracotta'
    )


@public
class NavEntry(Settings):
    """
    title: A local page, external URL, nested group, or generated API tree.
    attributes:
      title:
        type: str
      path:
        type: str | None
      url:
        type: str | None
      api:
        type: str | None
      children:
        type: list[NavEntry]
    """

    title: str = Field(min_length=1)
    path: str | None = None
    url: str | None = None
    api: str | None = None
    children: list[NavEntry] = Field(default_factory=list)

    @model_validator(mode='after')
    @typechecked
    def validate_target(self) -> NavEntry:
        """
        title: Require one unambiguous navigation target or a nonempty group.
        returns:
          type: NavEntry
        """
        targets = sum(
            value is not None for value in (self.path, self.url, self.api)
        )
        if targets > 1 or (targets == 0 and not self.children):
            raise ValueError('Use one of path, url, api, or children')
        if self.api is not None and self.children:
            raise ValueError('API entries generate their own children')
        return self


@public
class SidebarSettings(Settings):
    """
    title: A named menu selected by route prefixes or page front matter.
    attributes:
      id:
        type: str
      title:
        type: str
      paths:
        type: list[str]
      items:
        type: list[NavEntry]
    """

    id: str = Field(min_length=1)
    title: str
    paths: list[str] = Field(default_factory=list)
    items: list[NavEntry]


@public
class NavigationSettings(Settings):
    """
    title: Ordered navbar links and independently scoped documentation menus.
    attributes:
      navbar:
        type: list[NavEntry]
      sidebars:
        type: list[SidebarSettings]
      default_sidebar:
        type: str | None
    """

    navbar: list[NavEntry] = Field(default_factory=list)
    sidebars: list[SidebarSettings] = Field(default_factory=list)
    default_sidebar: str | None = None


@public
class SearchSettings(Settings):
    """
    title: Local full-text search over authored, notebook, and API content.
    attributes:
      enabled:
        type: bool
      limit:
        type: int
      min_length:
        type: int
    """

    enabled: bool = True
    limit: int = Field(default=8, ge=1, le=50)
    min_length: int = Field(default=2, ge=1, le=10)


@public
class Config(Settings):
    """
    title: Version one project configuration.
    attributes:
      schema_version:
        type: Literal[1]
      site:
        type: SiteSettings
      project:
        type: ProjectSettings
      docs_dir:
        type: str
      output_dir:
        type: str
      includes_dir:
        type: str
      data:
        type: dict[str, str]
      api:
        type: ApiSettings
      theme:
        type: ThemeSettings
      plugins:
        type: list[str]
      assets:
        type: list[str]
      navigation:
        type: NavigationSettings
      search:
        type: SearchSettings
    """

    schema_version: Literal[1] = 1
    site: SiteSettings
    project: ProjectSettings
    docs_dir: str = 'docs'
    output_dir: str = 'build'
    includes_dir: str = 'includes'
    data: dict[str, str] = Field(default_factory=dict)
    api: ApiSettings = Field(default_factory=ApiSettings)
    theme: ThemeSettings = Field(default_factory=ThemeSettings)
    plugins: list[str] = Field(default_factory=list)
    assets: list[str] = Field(default_factory=lambda: ['assets/**'])
    navigation: NavigationSettings = Field(default_factory=NavigationSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)


@public
class PageSettings(Settings):
    """
    title: Front matter supported on authored Markdown pages.
    attributes:
      title:
        type: str | None
      render:
        type: Literal[markdown, jinja]
      meta:
        type: dict[str, JsonValue]
      api_source:
        type: str | None
      layout:
        type: Literal[docs, full, landing]
      sidebar:
        type: str | bool
      toc:
        type: bool
      show_title:
        type: bool
      html:
        type: bool
      template:
        type: str
      search:
        type: bool
    """

    title: str | None = None
    render: Literal['markdown', 'jinja'] = 'markdown'
    meta: dict[str, JsonValue] = Field(default_factory=dict)
    api_source: str | None = None
    layout: Literal['docs', 'full', 'landing'] = 'docs'
    sidebar: str | bool = True
    toc: bool = True
    show_title: bool = True
    html: bool = False
    template: str = 'page.html'
    search: bool = True


@public
@typechecked
@dataclass(frozen=True, config=ConfigDict(strict=True))
class ApiVariant:
    """
    title: A statically collected callable signature and its own prose.
    attributes:
      signature:
        type: str
      documentation:
        type: dict[str, JsonValue]
      line:
        type: int | None
    """

    signature: str
    documentation: dict[str, JsonValue]
    line: int | None


@public
@typechecked
@dataclass(frozen=True, config=ConfigDict(strict=True))
class ApiSymbol:
    """
    title: An API declaration and its validated Douki documentation.
    attributes:
      identifier:
        type: str
      name:
        type: str
      kind:
        type: str
      signature:
        type: str
      source:
        type: str
      line:
        type: int | None
      documentation:
        type: dict[str, JsonValue]
      parent:
        type: str | None
      source_name:
        type: str | None
      canonical:
        type: str | None
      generated:
        type: bool
      variants:
        type: list[ApiVariant]
    """

    identifier: str
    name: str
    kind: str
    signature: str
    source: str
    line: int | None
    documentation: dict[str, JsonValue]
    parent: str | None = None
    source_name: str | None = None
    canonical: str | None = None
    generated: bool = False
    variants: list[ApiVariant] = field(default_factory=list)


@public
@typechecked
@dataclass(config=ConfigDict(strict=True))
class Page:
    """
    title: An authored or virtual page.
    attributes:
      route:
        type: str
      title:
        type: str
      body:
        type: str
      settings:
        type: PageSettings
      source:
        type: Path | None
      symbol:
        type: str | None
      anchors:
        type: set[str]
      notebook:
        type: Notebook | None
    """

    route: str
    title: str
    body: str
    settings: PageSettings
    source: Path | None = None
    symbol: str | None = None
    anchors: set[str] = field(default_factory=set)
    notebook: Notebook | None = None


@public
@typechecked
@dataclass(frozen=True, config=ConfigDict(strict=True))
class SiteBuild:
    """
    title: A complete validated site ready to write.
    attributes:
      files:
        type: dict[str, bytes]
      page_count:
        type: int
    """

    files: dict[str, bytes]
    page_count: int


@public
class NavigationItem(Settings):
    """
    title: A route-aware menu entry with nested pages or module accordions.
    attributes:
      title:
        type: str
      url:
        type: str | None
      current:
        type: bool
      active:
        type: bool
      children:
        type: list[NavigationItem]
      kind:
        type: str | None
      layout:
        type: Literal[nested, modules]
    """

    title: str
    url: str | None
    current: bool
    active: bool
    children: list[NavigationItem] = Field(default_factory=list)
    kind: str | None = None
    layout: Literal['nested', 'modules'] = 'nested'
