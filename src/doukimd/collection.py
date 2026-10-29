"""
title: Collect public Python APIs with declaration provenance and variants.
"""

from __future__ import annotations

import ast

from pathlib import Path
from typing import cast

import griffe

from plum import dispatch
from public import private
from pydantic import JsonValue

from doukimd.api import documentation, hidden, signature, source_path
from doukimd.errors import BuildError
from doukimd.models import ApiSymbol, ApiVariant
from doukimd.runtime import typechecked


@private
@typechecked
class FunctionCapture(griffe.Extension):
    """
    title: Retain every function instance before Griffe replaces names.
    attributes:
      functions:
        type: dict[str, list[griffe.Function]]
    """

    def __init__(self) -> None:
        """
        title: Initialize per-loader declaration storage.
        """
        self.functions: dict[str, list[griffe.Function]] = {}

    def on_function_instance(
        self,
        *,
        node: object,
        func: griffe.Function,
        agent: object,
        **kwargs: object,
    ) -> None:
        """
        title: Record source functions without importing project code.
        parameters:
          node:
            type: object
          func:
            type: griffe.Function
          agent:
            type: object
          kwargs:
            type: object
            variadic: keyword
        """
        del agent, kwargs
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.functions.setdefault(func.path, []).append(func)


@private
@typechecked
def identifier(path: str, source: str | None) -> str:
    """
    title: Namespace named sources while preserving unnamed identities.
    parameters:
      path:
        type: str
      source:
        type: str | None
    returns:
      type: str
    """
    return f'python:{source}:{path}' if source else f'python:{path}'


@private
@typechecked
def decorated(
    node: griffe.Function, target: str, seen: set[str] | None = None
) -> bool:
    """
    title: Resolve decorator aliases statically.
    parameters:
      node:
        type: griffe.Function
      target:
        type: str
      seen:
        type: set[str] | None
    returns:
      type: bool
    """
    seen = set() if seen is None else seen
    if node.path in seen:
        return False
    seen.add(node.path)
    for decorator in node.decorators:
        name = str(decorator.value).split('(', maxsplit=1)[0]
        try:
            head, dot, tail = name.partition('.')
            name = node.resolve(head) + (dot + tail if dot else '')
        except griffe.NameResolutionError:
            pass
        if name == target:
            return True
        try:
            resolved = node.modules_collection.get_member(name)
            aliases: set[str] = set()
            while isinstance(resolved, griffe.Alias):
                if name in aliases:
                    break
                aliases.add(name)
                name = resolved.target_path
                if name == target:
                    return True
                resolved = node.modules_collection.get_member(name)
        except (
            KeyError,
            griffe.AliasResolutionError,
            griffe.CyclicAliasError,
        ):
            pass
        if name.endswith('.dispatch'):
            try:
                dispatcher = node.modules_collection.get_member(name[:-9])
                if isinstance(dispatcher, griffe.Alias):
                    dispatcher = dispatcher.final_target
                if isinstance(dispatcher, griffe.Function) and decorated(
                    dispatcher, target, seen
                ):
                    return True
            except (
                KeyError,
                griffe.AliasResolutionError,
                griffe.CyclicAliasError,
            ):
                pass
    return False


@private
@typechecked
class Collector:
    """
    title: Visit supported declarations with explicit source confinement.
    attributes:
      root:
        type: Path
      search:
        type: Path
      source:
        type: str | None
      capture:
        type: FunctionCapture
      alias_stack:
        type: set[str]
      documents:
        type: dict[int, dict[str, object]]
    """

    root: Path
    search: Path
    source: str | None
    capture: FunctionCapture
    alias_stack: set[str]
    documents: dict[int, dict[str, object]]

    def __init__(
        self,
        root: Path,
        search: Path,
        source: str | None,
        capture: FunctionCapture,
    ) -> None:
        """
        title: Initialize a collector for one isolated source folder.
        parameters:
          root:
            type: Path
          search:
            type: Path
          source:
            type: str | None
          capture:
            type: FunctionCapture
        """
        self.root = root
        self.search = search
        self.source = source
        self.capture = capture
        self.alias_stack: set[str] = set()
        self.documents: dict[int, dict[str, object]] = {}

    def data(self, node: griffe.Object) -> dict[str, object]:
        """
        title: Validate source prose and distinguish generated members.
        parameters:
          node:
            type: griffe.Object
        returns:
          type: dict[str, object]
        """
        if id(node) in self.documents:
            return self.documents[id(node)]
        if node.docstring is None and (
            isinstance(node, griffe.Attribute)
            or (isinstance(node, griffe.Function) and not node.lineno)
        ):
            data: dict[str, object] = {}
            if isinstance(node, griffe.Attribute) and isinstance(
                node.parent, griffe.Class
            ):
                fields = self.data(node.parent).get('attributes', {})
                if isinstance(fields, dict):
                    field = fields.get(node.name)
                    if isinstance(field, dict) and isinstance(
                        field.get('description'), str
                    ):
                        data['summary'] = field['description']
        else:
            data = documentation(node, self.root)
        self.documents[id(node)] = data
        return data

    def make(
        self,
        node: griffe.Object,
        path: str,
        variants: list[ApiVariant] | None = None,
    ) -> ApiSymbol:
        """
        title: Preserve public identity separately from declaration origin.
        parameters:
          node:
            type: griffe.Object
          path:
            type: str
          variants:
            type: list[ApiVariant] | None
        returns:
          type: ApiSymbol
        """
        location = source_path(node)
        if not location.is_relative_to(self.search):
            raise BuildError(
                'api', 'Re-export escapes API source folder', location
            )
        kind = node.kind.value
        if isinstance(node, griffe.Function) and isinstance(
            node.parent, griffe.Class
        ):
            kind = 'method'
        if isinstance(node, griffe.Attribute):
            kind = self.attribute_kind(node)
        parent = path.rsplit('.', 1)[0] if '.' in path else None
        display = variants[0].signature if variants else signature(node)
        public_name = path.rsplit('.', 1)[-1]
        if display.startswith(node.name):
            display = public_name + display[len(node.name) :]
        return ApiSymbol(
            identifier=identifier(path, self.source),
            name=path.rsplit('.', 1)[-1],
            kind=kind,
            signature=display,
            source=location.relative_to(self.root).as_posix(),
            line=(
                variants[0].line
                if variants
                else node.lineno
                or (node.parent.lineno if node.parent is not None else None)
            ),
            documentation=(
                variants[0].documentation
                if variants
                else cast(dict[str, JsonValue], self.data(node))
            ),
            parent=identifier(parent, self.source) if parent else None,
            source_name=self.source,
            canonical=identifier(node.path, self.source),
            generated=isinstance(node, griffe.Function)
            and not bool(node.lineno),
            variants=variants or [],
        )

    def attribute_kind(self, node: griffe.Attribute) -> str:
        """
        title: Distinguish properties, type aliases, enum values, and fields.
        parameters:
          node:
            type: griffe.Attribute
        returns:
          type: str
        """
        if 'property' in node.labels:
            return 'property'
        annotation = str(node.annotation)
        try:
            annotation = node.resolve(annotation)
        except griffe.NameResolutionError:
            pass
        if (
            annotation
            in {'TypeAlias', 'typing.TypeAlias', 'typing_extensions.TypeAlias'}
            or 'type_alias' in node.labels
        ):
            return 'type-alias'
        if isinstance(node.parent, griffe.Class):
            for base in node.parent.bases:
                name = str(base)
                try:
                    name = node.parent.resolve(name)
                except griffe.NameResolutionError:
                    pass
                if name in {
                    'enum.Enum',
                    'enum.IntEnum',
                    'enum.StrEnum',
                    'enum.Flag',
                    'enum.IntFlag',
                }:
                    return 'enum-member'
        return 'attribute'

    def callable_variants(self, node: griffe.Function) -> list[ApiVariant]:
        """
        title: Retain dispatch families and declared typing overloads.
        parameters:
          node:
            type: griffe.Function
        returns:
          type: list[ApiVariant]
        """
        definitions = self.capture.functions.get(node.path, [node])
        selected = node.overloads or definitions
        if len(definitions) > 1 and not node.overloads:
            if not all(
                decorated(item, 'plum.dispatch')
                or (
                    decorated(definitions[0], 'plum.dispatch')
                    and any(
                        str(decorator.value) == f'{node.name}.dispatch'
                        for decorator in item.decorators
                    )
                )
                for item in definitions
            ):
                raise BuildError(
                    'api', f'Unsupported repeated declaration: {node.path}'
                )
        if len(selected) <= 1:
            return []
        result: list[ApiVariant] = []
        for item in selected:
            if hidden(item):
                continue
            data = self.data(item) if item.docstring else self.data(node)
            result.append(
                ApiVariant(
                    signature(item),
                    cast(dict[str, JsonValue], data),
                    item.lineno,
                )
            )
        return result

    @dispatch
    @typechecked
    def visit(self, node: object, path: str) -> list[ApiSymbol]:
        """
        title: Reject unsupported declarations rather than omitting them.
        parameters:
          node:
            type: object
          path:
            type: str
        returns:
          type: list[ApiSymbol]
        """
        raise BuildError(
            'api', f'Unsupported declaration: {type(node).__name__}'
        )

    @dispatch
    @typechecked
    def visit(self, node: griffe.Alias, path: str) -> list[ApiSymbol]:
        """
        title: Follow explicitly exported aliases without runtime imports.
        parameters:
          node:
            type: griffe.Alias
          path:
            type: str
        returns:
          type: list[ApiSymbol]
        """
        try:
            target = node.final_target
        except (griffe.AliasResolutionError, griffe.CyclicAliasError) as error:
            raise BuildError(
                'api', f'Unresolved re-export: {node.path}'
            ) from error
        if target.path in self.alias_stack:
            raise BuildError('api', f'Cyclic re-export: {node.path}')
        self.alias_stack.add(target.path)
        try:
            return self.visit(target, path)
        finally:
            self.alias_stack.remove(target.path)

    @dispatch
    @typechecked
    def visit(self, node: griffe.Function, path: str) -> list[ApiSymbol]:
        """
        title: Collect callable declarations and all statically known variants.
        parameters:
          node:
            type: griffe.Function
          path:
            type: str
        returns:
          type: list[ApiSymbol]
        """
        if hidden(node) and all(
            hidden(item)
            for item in self.capture.functions.get(node.path, [node])
        ):
            return []
        return [self.make(node, path, self.callable_variants(node))]

    @dispatch
    @typechecked
    def visit(self, node: griffe.Attribute, path: str) -> list[ApiSymbol]:
        """
        title: Collect documented or explicitly exported data declarations.
        parameters:
          node:
            type: griffe.Attribute
          path:
            type: str
        returns:
          type: list[ApiSymbol]
        """
        return [] if hidden(node) else [self.make(node, path)]

    @dispatch
    @typechecked
    def visit(
        self, node: griffe.Module | griffe.Class, path: str
    ) -> list[ApiSymbol]:
        """
        title: Collect exported members and configured package submodules.
        parameters:
          node:
            type: griffe.Module | griffe.Class
          path:
            type: str
        returns:
          type: list[ApiSymbol]
        """
        if hidden(node):
            return []
        result = [self.make(node, path)]
        exports = node.exports if isinstance(node, griffe.Module) else None
        if exports is not None:
            if any(not isinstance(name, str) for name in exports):
                raise BuildError('api', f'Dynamic exports: {node.path}')
            missing = set(exports).difference(node.members)
            if missing:
                raise BuildError(
                    'api', f'Unresolved exports in {node.path}: {missing}'
                )
        for name, child in sorted(node.members.items()):
            if isinstance(child, griffe.Module):
                result.extend(self.visit(child, f'{path}.{name}'))
                continue
            if exports is not None and name not in exports:
                continue
            if isinstance(child, griffe.Alias) and exports is None:
                continue
            result.extend(self.visit(child, f'{path}.{name}'))
        return result
