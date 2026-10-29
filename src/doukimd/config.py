"""
title: Load configuration and confine all project paths.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from public import private, public
from pydantic import JsonValue, TypeAdapter, ValidationError

from doukimd.errors import BuildError
from doukimd.models import Config
from doukimd.runtime import typechecked


@private
class UniqueLoader(yaml.SafeLoader):
    """
    title: Reject duplicate YAML mapping keys.
    """

    @typechecked
    def construct_mapping(
        self, node: yaml.MappingNode, deep: bool = False
    ) -> dict[object, object]:
        """
        title: Construct a mapping after checking its keys.
        parameters:
          node:
            type: yaml.MappingNode
          deep:
            type: bool
        returns:
          type: dict[object, object]
        """
        self.flatten_mapping(node)
        result: dict[object, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise BuildError(
                    'metadata', 'YAML mapping keys must be strings'
                )
            if key in result:
                raise BuildError('metadata', f'Duplicate YAML key: {key}')
            result[key] = self.construct_object(value_node, deep=deep)
        return result


@public
@typechecked
def read_yaml(text: str, source: Path) -> dict[str, object]:
    """
    title: Read a YAML mapping containing JSON-compatible values.
    parameters:
      text:
        type: str
      source:
        type: Path
    returns:
      type: dict[str, object]
    """
    try:
        raw = yaml.load(text, Loader=UniqueLoader)
        validated = TypeAdapter(dict[str, JsonValue]).validate_python(
            raw, strict=True
        )
        return dict(validated)
    except (yaml.YAMLError, ValidationError) as error:
        raise BuildError('metadata', str(error), source) from error
    except BuildError as error:
        raise BuildError(error.phase, error.message, source) from error


@public
@typechecked
def project_path(root: Path, value: str) -> Path:
    """
    title: Resolve a relative project path without following outside symlinks.
    parameters:
      root:
        type: Path
      value:
        type: str
    returns:
      type: Path
    """
    relative = Path(value)
    if relative.is_absolute() or '..' in relative.parts:
        raise BuildError(
            'config', f'Expected a relative project path: {value}'
        )
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise BuildError('config', f'Path escapes project: {value}')
    return resolved


@public
@typechecked
def load_config(path: Path) -> Config:
    """
    title: Load and validate a DoukiMD project configuration.
    parameters:
      path:
        type: Path
    returns:
      type: Config
    """
    try:
        raw = read_yaml(path.read_text(encoding='utf-8'), path)
        config = Config.model_validate(raw)
    except (OSError, UnicodeError, ValidationError) as error:
        raise BuildError('config', str(error), path) from error
    if not config.site.title.strip() or not config.project.name.strip():
        raise BuildError(
            'config', 'Site title and project name cannot be empty'
        )
    names = config.plugins
    if len(names) != len(set(names)):
        raise BuildError('config', 'Plugin names must be unique', path)
    return config


@public
@typechecked
def load_data(root: Path, config: Config) -> dict[str, object]:
    """
    title: Load explicitly configured data mappings.
    parameters:
      root:
        type: Path
      config:
        type: Config
    returns:
      type: dict[str, object]
    """
    result: dict[str, object] = {}
    for name, value in config.data.items():
        path = project_path(root, value)
        try:
            result[name] = read_yaml(path.read_text(encoding='utf-8'), path)
        except (OSError, UnicodeError) as error:
            raise BuildError('metadata', str(error), path) from error
    return result
