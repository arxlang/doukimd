"""
title: Collect Python declarations without importing project code.
"""

from __future__ import annotations

import json
import re

from importlib.resources import files
from pathlib import Path
from typing import cast

import griffe

from jsonschema import Draft202012Validator
from plum import dispatch
from public import private, public
from pydantic import JsonValue

from doukimd.config import project_path, read_yaml
from doukimd.errors import BuildError
from doukimd.models import ApiSymbol, Config
from doukimd.runtime import typechecked


@private
@typechecked
def source_path(node: griffe.Object) -> Path:
    """
    title: Reject namespace packages without a single source file.
    parameters:
      node:
        type: griffe.Object
    returns:
      type: Path
    """
    path = node.filepath
    if not isinstance(path, Path):
        raise BuildError('api', f'No single source file for {node.path}')
    return path.resolve()


@private
@typechecked
def documentation(node: griffe.Object, root: Path) -> dict[str, object]:
    """
    title: Validate a source docstring using the installed Douki schema.
    parameters:
      node:
        type: griffe.Object
      root:
        type: Path
    returns:
      type: dict[str, object]
    """
    path = source_path(node)
    if not path.is_relative_to(root):
        raise BuildError('api', 'API source escapes the project', path)
    if node.docstring is None:
        raise BuildError(
            'douki', f'Missing Douki docstring: {node.path}', path
        )
    data = read_yaml(node.docstring.value, path)
    schema = json.loads(
        files('douki').joinpath('schema.json').read_text(encoding='utf-8')
    )
    errors = sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda error: str(list(error.path)),
    )
    if errors:
        raise BuildError(
            'douki',
            f'{node.path}: Douki schema: '
            + '; '.join(error.message for error in errors),
            path,
        )
    if isinstance(node, griffe.Function) and 'parameters' in data:
        expected = {
            parameter.name
            for parameter in node.parameters
            if not (
                isinstance(node.parent, griffe.Class)
                and 'staticmethod' not in node.labels
                and parameter.name in {'self', 'cls'}
            )
        }
        parameters = cast(dict[str, object], data['parameters'])
        if set(parameters) != expected:
            raise BuildError(
                'douki',
                f'{node.path}: documented parameters do not match signature',
                path,
            )
    return data


@private
@dispatch
@typechecked
def signature(node: object) -> str:
    """
    title: Reject unsupported API declarations.
    parameters:
      node:
        type: object
    returns:
      type: str
    """
    raise BuildError('api', f'Unsupported declaration: {type(node).__name__}')


@dispatch
@typechecked
def signature(node: griffe.Module) -> str:
    """
    title: Display a module name.
    parameters:
      node:
        type: griffe.Module
    returns:
      type: str
    """
    return node.path


@dispatch
@typechecked
def signature(node: griffe.Class | griffe.Function) -> str:
    """
    title: Preserve the source signature through Griffe.
    parameters:
      node:
        type: griffe.Class | griffe.Function
    returns:
      type: str
    """
    return node.signature()


@private
@typechecked
def hidden(node: griffe.Object) -> bool:
    """
    title: Honor explicit visibility rather than underscore naming heuristics.
    parameters:
      node:
        type: griffe.Object
    returns:
      type: bool
    """
    for decorator in getattr(node, 'decorators', []):
        name = str(decorator.value).split('(', maxsplit=1)[0]
        try:
            resolved = node.resolve(name)
        except griffe.NameResolutionError:
            resolved = name
        if resolved == 'public.private':
            return True
    if node.docstring is not None:
        data = read_yaml(node.docstring.value, source_path(node))
        return data.get('visibility') in {'private', 'protected', 'internal'}
    return False


@private
@typechecked
def symbol(node: griffe.Object, root: Path) -> ApiSymbol:
    """
    title: Normalize a supported declaration into the shared symbol model.
    parameters:
      node:
        type: griffe.Object
      root:
        type: Path
    returns:
      type: ApiSymbol
    """
    data = documentation(node, root)
    return ApiSymbol(
        identifier=f'python:{node.path}',
        name=node.name,
        kind=(
            'method'
            if isinstance(node, griffe.Function)
            and isinstance(node.parent, griffe.Class)
            else node.kind.value
        ),
        signature=signature(node),
        source=source_path(node).relative_to(root).as_posix(),
        line=node.lineno,
        documentation=cast(dict[str, JsonValue], data),
        parent=(
            f'python:{node.parent.path}' if node.parent is not None else None
        ),
    )


@private
@dispatch
@typechecked
def visit(node: object, root: Path) -> list[ApiSymbol]:
    """
    title: Fail closed for unsupported API nodes.
    parameters:
      node:
        type: object
      root:
        type: Path
    returns:
      type: list[ApiSymbol]
    """
    raise BuildError('api', f'Unsupported declaration: {type(node).__name__}')


@dispatch
@typechecked
def visit(node: griffe.Function, root: Path) -> list[ApiSymbol]:
    """
    title: Collect a function or method declaration.
    parameters:
      node:
        type: griffe.Function
      root:
        type: Path
    returns:
      type: list[ApiSymbol]
    """
    if hidden(node):
        return []
    if node.overloads:
        raise BuildError(
            'api', f'Overload sets are not supported: {node.path}'
        )
    return [symbol(node, root)]


@dispatch
@typechecked
def visit(node: griffe.Module | griffe.Class, root: Path) -> list[ApiSymbol]:
    """
    title: Collect declarations and explicitly selected public members.
    parameters:
      node:
        type: griffe.Module | griffe.Class
      root:
        type: Path
    returns:
      type: list[ApiSymbol]
    """
    if hidden(node):
        return []
    result = [symbol(node, root)]
    exports = node.exports if isinstance(node, griffe.Module) else None
    if exports is not None:
        if any(not isinstance(name, str) for name in exports):
            raise BuildError('api', f'Dynamic exports: {node.path}')
        missing = set(exports).difference(node.members)
        if missing:
            raise BuildError('api', f'Unresolved exports: {missing}')
    for name, child in sorted(node.members.items()):
        if exports is not None and name not in exports:
            continue
        if isinstance(child, griffe.Alias):
            if exports is not None:
                raise BuildError(
                    'api',
                    f'Explicit re-export is not supported yet: {child.path}',
                    source_path(node),
                )
            continue
        if isinstance(child, (griffe.Module, griffe.Class, griffe.Function)):
            result.extend(visit(child, root))
        elif exports is not None:
            raise BuildError(
                'api',
                f'Exported attributes are not supported yet: {child.path}',
                source_path(node),
            )
    return result


@public
@typechecked
def collect_api(root: Path, config: Config) -> dict[str, ApiSymbol]:
    """
    title: Collect configured modules using static analysis only.
    parameters:
      root:
        type: Path
      config:
        type: Config
    returns:
      type: dict[str, ApiSymbol]
    """
    inventory: dict[str, ApiSymbol] = {}
    for source in config.api.sources:
        search = project_path(root, source.root)
        for module in source.modules:
            if re.fullmatch(r'[A-Za-z]\w*(?:\.[A-Za-z]\w*)*', module) is None:
                raise BuildError('api', f'Invalid module name: {module}')
            try:
                node = griffe.load(
                    module,
                    search_paths=[search],
                    allow_inspection=False,
                    resolve_aliases=False,
                )
            except (
                griffe.LoadingError,
                griffe.NameResolutionError,
                ModuleNotFoundError,
                KeyError,
                OSError,
                SyntaxError,
            ) as error:
                raise BuildError('api', str(error), search) from error
            for item in visit(node, root):
                if item.identifier in inventory:
                    raise BuildError(
                        'api', f'Duplicate API symbol: {item.identifier}'
                    )
                inventory[item.identifier] = item
    return inventory
