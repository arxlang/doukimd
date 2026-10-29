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


@dispatch
@typechecked
def signature(node: griffe.Attribute) -> str:
    """
    title: Display a data declaration without evaluating its value.
    parameters:
      node:
        type: griffe.Attribute
    returns:
      type: str
    """
    annotation = f': {node.annotation}' if node.annotation else ''
    value = f' = {node.value}' if node.value is not None else ''
    return f'{node.name}{annotation}{value}'


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
def visit(node: object, root: Path) -> list[ApiSymbol]:
    """
    title: Visit a declaration using the default unscoped collector.
    parameters:
      node:
        type: object
      root:
        type: Path
    returns:
      type: list[ApiSymbol]
    """
    from doukimd.collection import Collector, FunctionCapture

    return cast(
        list[ApiSymbol],
        Collector(root, root, None, FunctionCapture()).visit(
            node, getattr(node, 'path', '')
        ),
    )


@public
@typechecked
def collect_api(root: Path, config: Config) -> dict[str, ApiSymbol]:
    """
    title: Collect isolated source folders without importing project code.
    parameters:
      root:
        type: Path
      config:
        type: Config
    returns:
      type: dict[str, ApiSymbol]
    """
    from doukimd.collection import Collector, FunctionCapture

    inventory: dict[str, ApiSymbol] = {}
    names: set[str] = set()
    for source in config.api.sources:
        if source.name is not None:
            if source.name in names:
                raise BuildError('api', f'Duplicate API source: {source.name}')
            names.add(source.name)
        search = project_path(root, source.root)
        if not search.is_dir():
            raise BuildError('api', 'API source folder does not exist', search)
        for path in search.rglob('*'):
            if path.is_symlink() and not path.resolve().is_relative_to(search):
                raise BuildError(
                    'api', 'API source escapes selected folder', path
                )
        capture = FunctionCapture()
        modules = list(source.modules)
        loader_search = search
        if not modules:
            if (search / '__init__.py').is_file():
                loader_search = search.parent
                modules = [search.name]
            else:
                for directory in search.iterdir():
                    if (
                        directory.is_dir()
                        and not (directory / '__init__.py').is_file()
                        and any(directory.rglob('*.py'))
                    ):
                        raise BuildError(
                            'api',
                            'Namespace packages are unsupported',
                            directory,
                        )
                modules = sorted(
                    [path.stem for path in search.glob('*.py')]
                    + [
                        path.name
                        for path in search.iterdir()
                        if path.is_dir() and (path / '__init__.py').is_file()
                    ]
                )
            if not modules:
                raise BuildError(
                    'api', 'No Python modules in source folder', search
                )
        loader = griffe.GriffeLoader(
            search_paths=[loader_search],
            allow_inspection=False,
            extensions=griffe.load_extensions(capture),
        )
        nodes: list[griffe.Object | griffe.Alias] = []
        try:
            for module in modules:
                if (
                    re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', module)
                    is None
                ):
                    raise BuildError('api', f'Invalid module name: {module}')
                nodes.append(loader.load(module))
            loader.resolve_aliases(external=False)
            collector = Collector(root, search, source.name, capture)
            for node in nodes:
                for item in collector.visit(node, node.path):
                    if item.identifier in inventory:
                        raise BuildError(
                            'api', f'Duplicate API symbol: {item.identifier}'
                        )
                    inventory[item.identifier] = item
        except (
            griffe.LoadingError,
            griffe.NameResolutionError,
            griffe.AliasResolutionError,
            griffe.CyclicAliasError,
            ModuleNotFoundError,
            KeyError,
            OSError,
            SyntaxError,
        ) as error:
            raise BuildError('api', str(error), search) from error
    return inventory
