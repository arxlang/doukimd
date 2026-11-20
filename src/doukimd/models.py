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
from doukimd.output import PublishedFiles
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
        description: Display title for the page or navigation entry.
      base_url:
        description: Public base URL used for site links.
      description:
        description: Human-readable description of the site or entry.
      logo:
        description: Docs-relative path to the site logo.
      logo_alt:
        description: Accessible alternative text for the logo.
      favicon:
        description: Docs-relative path to the favicon.
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
        description: Name used to identify the requested item.
      version:
        description: Project version displayed by the theme.
    """

    name: str
    version: str = ''


@public
class PythonSource(Settings):
    """
    title: Configure static collection of explicitly selected Python modules.
    attributes:
      language:
        description: Source language used for highlighting or collection.
      name:
        description: Name used to identify the requested item.
      root:
        description: Project root used to resolve relative paths.
      modules:
        description: Python import paths selected within the source folder.
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
        description: Isolated source folders selected for API collection.
      generate_pages:
        description: Whether to generate standalone API reference pages.
    """

    sources: list[PythonSource] = Field(default_factory=list)
    generate_pages: bool = True


@public
class ThemeSettings(Settings):
    """
    title: Frontend framework, color preference, and local template overrides.
    attributes:
      stylesheets:
        description: Additional docs-relative stylesheet paths.
      directory:
        description: Directory containing the selected project resources.
      framework:
        description: Selected bundled CSS framework.
      color_mode:
        description: Initial light, dark, or automatic appearance.
      palette:
        description: Selected semantic color palette.
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
        description: Display title for the page or navigation entry.
      path:
        description: Path or qualified declaration name to resolve.
      url:
        description: Link destination to validate or rebase.
      api:
        description: Indexed API declarations used for symbol lookup.
      children:
        description: Immediate children in display order.
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
          description: Validated navigation entry.
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
        description: Stable identifier for the configured entry.
      title:
        description: Display title for the page or navigation entry.
      paths:
        description: Paths selected for processing.
      items:
        description: Entries to process in display order.
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
        description: Configured top-level navigation menus.
      sidebars:
        description: Configured sidebar menus.
      default_sidebar:
        description: Sidebar selected when no more specific rule applies.
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
        description: Whether this feature is enabled.
      limit:
        description: Maximum number of results to display.
      min_length:
        description: Minimum query length before searching.
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
        description: Configuration schema revision.
      site:
        description: Indexed site pages and output destinations.
      project:
        description: Project configuration or temporary project directory.
      docs_dir:
        description: Project-relative directory containing authored pages.
      output_dir:
        description: Project-relative directory for generated site output.
      includes_dir:
        description: Project-relative directory containing content templates.
      data:
        description: Structured content or template data to process.
      api:
        description: Indexed API declarations used for symbol lookup.
      theme:
        description: Theme settings controlling HTML presentation.
      plugins:
        description: Explicitly enabled plugin entry points.
      assets:
        description: Asset destinations and bytes included in the build.
      navigation:
        description: Navigation configuration or selected sidebar entries.
      search:
        description: Selected source folder that confines API collection.
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
        description: Display title for the page or navigation entry.
      render:
        description: Whether the page body uses Markdown alone or enabled
          Jinja.
      meta:
        description: Literal page metadata exposed to templates.
      api_source:
        description: Default named API source for page references.
      layout:
        description: Presentation layout used for this menu or page.
      sidebar:
        description: Sidebar selected for this page.
      toc:
        description: Whether to display page section links.
      show_title:
        description: Whether to display the page title.
      html:
        description: Whether authored page HTML is enabled, or rendered HTML
          content.
      template:
        description: Template or macro used to render the current content.
      search:
        description: Selected source folder that confines API collection.
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
        description: Display signature derived statically from source.
      documentation:
        description: Validated documentation fields for the declaration.
      line:
        description: Source line containing the declaration.
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
        description: Stable, source-qualified API identity.
      name:
        description: Name used to identify the requested item.
      kind:
        description: Declaration, navigation, or output kind.
      signature:
        description: Display signature derived statically from source.
      source:
        description: Source content or configured API source name.
      line:
        description: Source line containing the declaration.
      documentation:
        description: Validated documentation fields for the declaration.
      parent:
        description: Parent declaration, navigation entry, or output element.
      source_name:
        description: Configured source name used to scope API identities.
      canonical:
        description: Identity of the original declaration behind a re-export.
      generated:
        description: Whether the declaration was generated by the source
          model.
      variants:
        description: Callable signatures and documentation in declaration
          order.
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
        description: Planned output path relative to the site root.
      title:
        description: Display title for the page or navigation entry.
      body:
        description: Page body before final HTML rendering.
      settings:
        description: Validated settings controlling the current operation.
      source:
        description: Source content or configured API source name.
      symbol:
        description: API declaration to resolve or render.
      anchors:
        description: Document heading anchors available for link validation.
      notebook:
        description: Validated notebook content associated with the page.
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
@dataclass(
    frozen=True, config=ConfigDict(strict=True, arbitrary_types_allowed=True)
)
class SiteBuild:
    """
    title: A complete validated site and its generated artifacts.
    attributes:
      files:
        description: Artifacts keyed by relative destination; published builds
          read bytes on demand from their output directory.
      page_count:
        description: Number of pages produced by the build.
    """

    # Check the disk view first: Pydantic's dict validator would otherwise
    # eagerly read every artifact while selecting the union branch.
    files: PublishedFiles | dict[str, bytes]
    page_count: int


@public
class NavigationItem(Settings):
    """
    title: A route-aware menu entry with nested pages or module accordions.
    attributes:
      title:
        description: Display title for the page or navigation entry.
      url:
        description: Link destination to validate or rebase.
      current:
        description: Current page route or navigation selection.
      active:
        description: Whether this entry belongs to the selected navigation
          branch.
      children:
        description: Immediate children in display order.
      kind:
        description: Declaration, navigation, or output kind.
      layout:
        description: Presentation layout used for this menu or page.
    """

    title: str
    url: str | None
    current: bool
    active: bool
    children: list[NavigationItem] = Field(default_factory=list)
    kind: str | None = None
    layout: Literal['nested', 'modules'] = 'nested'
