"""
title: Collect Python declarations without importing project code.
"""

from __future__ import annotations

import json
import re

from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Literal, cast

import griffe

from douki import DocumentationError, Parameter, enrich
from douki import Signature as DocumentationSignature
from jsonschema import Draft202012Validator
from plum import dispatch
from public import private, public

from doukimd.config import project_path, read_yaml
from doukimd.errors import BuildError
from doukimd.models import ApiSymbol, Config
from doukimd.runtime import typechecked


@private
@lru_cache(maxsize=1)
@typechecked
def documentation_validator() -> Draft202012Validator:
    """
    title: Reuse the validator for the installed Douki schema.
    returns:
      description: Cached validator for the installed schema.
    """
    schema = json.loads(
        files('douki').joinpath('schema.json').read_text(encoding='utf-8')
    )
    return Draft202012Validator(schema)


@private
@typechecked
def source_path(node: griffe.Object) -> Path:
    """
    title: Reject namespace packages without a single source file.
    parameters:
      node:
        description: Source declaration or parsed document node to process.
    returns:
      description: Resolved path to the declaration source file.
    """
    path = node.filepath
    if not isinstance(path, Path):
        raise BuildError('api', f'No single source file for {node.path}')
    return path.resolve()


@private
@dispatch
@typechecked
def annotation_signature(node: object) -> DocumentationSignature:
    """
    title: Reject unsupported static annotation adapters.
    parameters:
      node: Declaration whose annotation metadata is requested.
    returns: Static metadata accepted by Douki's public enrichment API.
    """
    raise BuildError('api', f'Unsupported declaration: {type(node).__name__}')


@dispatch
@typechecked
def annotation_signature(
    node: griffe.Module | griffe.Attribute,
) -> DocumentationSignature:
    """
    title: Retain property return annotations without inspecting values.
    parameters:
      node: Module or data declaration being documented.
    returns: Property return annotation or empty non-callable metadata.
    """
    if isinstance(node, griffe.Attribute) and 'property' in node.labels:
        return DocumentationSignature(
            parameters=(),
            returns=str(node.annotation)
            if node.annotation is not None
            else '',
        )
    return DocumentationSignature()


@dispatch
@typechecked
def annotation_signature(node: griffe.Class) -> DocumentationSignature:
    """
    title: Supply class field annotations without evaluating their values.
    parameters:
      node: Class whose locally declared attributes are being documented.
    returns: Annotated fields available for documentation enrichment.
    """
    return DocumentationSignature(
        attributes=tuple(
            Parameter(name, str(member.annotation))
            for name, member in node.members.items()
            if isinstance(member, griffe.Attribute)
            and member.annotation is not None
        )
    )


@dispatch
@typechecked
def annotation_signature(node: griffe.Function) -> DocumentationSignature:
    """
    title: Adapt static callable annotations and variadic parameter kinds.
    parameters:
      node: Callable declaration, including one dispatch or overload variant.
    returns: Explicit parameters and return annotation for Douki enrichment.
    """
    kinds: dict[
        griffe.ParameterKind,
        Literal[
            'regular',
            'positional_only',
            'keyword_only',
            'var_positional',
            'var_keyword',
        ],
    ] = {
        griffe.ParameterKind.positional_only: 'positional_only',
        griffe.ParameterKind.positional_or_keyword: 'regular',
        griffe.ParameterKind.keyword_only: 'keyword_only',
        griffe.ParameterKind.var_positional: 'var_positional',
        griffe.ParameterKind.var_keyword: 'var_keyword',
    }
    return DocumentationSignature(
        parameters=tuple(
            Parameter(
                parameter.name,
                str(parameter.annotation)
                if parameter.annotation is not None
                else '',
                kinds[parameter.kind],
            )
            for parameter in node.parameters
            if not (
                isinstance(node.parent, griffe.Class)
                and 'staticmethod' not in node.labels
                and parameter.name in {'self', 'cls'}
            )
        ),
        returns=str(node.returns) if node.returns is not None else '',
    )


@private
@typechecked
def documentation(node: griffe.Object, root: Path) -> dict[str, object]:
    """
    title: Validate a source docstring using the installed Douki schema.
    parameters:
      node:
        description: Source declaration or parsed document node to process.
      root:
        description: Project root used to resolve relative paths.
    returns:
      description: Validated documentation fields from the source.
    """
    path = source_path(node)
    if not path.is_relative_to(root):
        raise BuildError('api', 'API source escapes the project', path)
    if node.docstring is None:
        raise BuildError(
            'douki', f'Missing Douki docstring: {node.path}', path
        )
    data = read_yaml(node.docstring.value, path)
    errors = sorted(
        documentation_validator().iter_errors(data),
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
    try:
        return enrich(node.docstring.value, annotation_signature(node))
    except DocumentationError as error:
        raise BuildError('douki', f'{node.path}: {error}', path) from error


@private
@dispatch
@typechecked
def signature(node: object) -> str:
    """
    title: Reject unsupported API declarations.
    parameters:
      node:
        description: Source declaration or parsed document node to process.
    returns:
      description: Display signature preserving source annotations.
    """
    raise BuildError('api', f'Unsupported declaration: {type(node).__name__}')


@dispatch
@typechecked
def signature(node: griffe.Module) -> str:
    """
    title: Display a module name.
    parameters:
      node:
        description: Source declaration or parsed document node to process.
    returns:
      description: Display signature preserving source annotations.
    """
    return node.path


@dispatch
@typechecked
def signature(node: griffe.Class | griffe.Function) -> str:
    """
    title: Preserve the source signature through Griffe.
    parameters:
      node:
        description: Source declaration or parsed document node to process.
    returns:
      description: Display signature preserving source annotations.
    """
    return node.signature()


@dispatch
@typechecked
def signature(node: griffe.Attribute) -> str:
    """
    title: Display a data declaration without evaluating its value.
    parameters:
      node:
        description: Source declaration or parsed document node to process.
    returns:
      description: Display signature preserving source annotations.
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
        description: Source declaration or parsed document node to process.
    returns:
      description: Whether explicit metadata marks the declaration as private.
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
        description: Source declaration or parsed document node to process.
      root:
        description: Project root used to resolve relative paths.
    returns:
      description: Processed declarations or document tokens.
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
        description: Project root used to resolve relative paths.
      config:
        description: Validated project settings or their configuration file.
    returns:
      description: Collected declarations keyed by stable API identity.
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
