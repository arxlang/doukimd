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

JSON_MAPPING = TypeAdapter(dict[str, JsonValue])


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
            description: Source declaration or parsed document node to process.
          deep:
            description: Whether to process nested mapping values.
        returns:
          description: Mapping whose keys have been checked for duplicates.
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
        description: Text content to process.
      source:
        description: Source content or configured API source name.
    returns:
      description: Validated YAML mapping containing JSON-compatible values.
    """
    try:
        raw = yaml.load(text, Loader=UniqueLoader)
        validated = JSON_MAPPING.validate_python(raw, strict=True)
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
        description: Project root used to resolve relative paths.
      value:
        description: Input value to validate or render.
    returns:
      description: Resolved path confined to the project root.
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
        description: Path or qualified declaration name to resolve.
    returns:
      description: Validated project configuration.
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
        description: Project root used to resolve relative paths.
      config:
        description: Validated project settings or their configuration file.
    returns:
      description: Configured data mappings keyed by template namespace.
    """
    result: dict[str, object] = {}
    for name, value in config.data.items():
        path = project_path(root, value)
        try:
            result[name] = read_yaml(path.read_text(encoding='utf-8'), path)
        except (OSError, UnicodeError) as error:
            raise BuildError('metadata', str(error), path) from error
    return result
