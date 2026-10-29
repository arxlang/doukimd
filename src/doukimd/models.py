"""
title: Validated configuration and build models.
"""

from __future__ import annotations

from dataclasses import field
from pathlib import Path
from typing import Literal

from public import public
from pydantic import BaseModel, ConfigDict, Field, JsonValue
from pydantic.dataclasses import dataclass

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
    """

    title: str
    base_url: str = ''


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
      root:
        type: str
      modules:
        type: list[str]
    """

    language: Literal['python'] = 'python'
    root: str = 'src'
    modules: list[str] = Field(min_length=1)


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
      directory:
        type: str | None
      framework:
        type: Literal[bootstrap, none]
      color_mode:
        type: Literal[auto, light, dark]
      palette:
        type: Literal[terracotta, ocean, forest, violet, slate]
    """

    directory: str | None = None
    framework: Literal['bootstrap', 'none'] = 'bootstrap'
    color_mode: Literal['auto', 'light', 'dark'] = 'auto'
    palette: Literal['terracotta', 'ocean', 'forest', 'violet', 'slate'] = (
        'terracotta'
    )


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
    """

    title: str | None = None
    render: Literal['markdown', 'jinja'] = 'markdown'
    meta: dict[str, JsonValue] = Field(default_factory=dict)


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
    """

    identifier: str
    name: str
    kind: str
    signature: str
    source: str
    line: int | None
    documentation: dict[str, JsonValue]
    parent: str | None = None


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
    """

    route: str
    title: str
    body: str
    settings: PageSettings
    source: Path | None = None
    symbol: str | None = None
    anchors: set[str] = field(default_factory=set)


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
    title: A route-aware navigation entry with nested API children.
    attributes:
      title:
        type: str
      url:
        type: str
      current:
        type: bool
      active:
        type: bool
      children:
        type: list[NavigationItem]
      kind:
        type: str | None
    """

    title: str
    url: str
    current: bool
    active: bool
    children: list[NavigationItem] = Field(default_factory=list)
    kind: str | None = None
