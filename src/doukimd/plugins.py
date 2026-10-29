"""
title: Explicitly enabled plugin context providers.
"""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import cast

import pluggy

from public import private, public
from pydantic import JsonValue, TypeAdapter, ValidationError

from doukimd.errors import BuildError
from doukimd.models import Config
from doukimd.runtime import typechecked

hookspec = pluggy.HookspecMarker('doukimd')
hookimpl = pluggy.HookimplMarker('doukimd')


@private
class ContextHooks:
    """
    title: Supported version one plugin hook specifications.
    """

    @hookspec
    @typechecked
    def doukimd_context(self, config: Config) -> dict[str, object]:
        """
        title: Provide data under the plugin's own template namespace.
        parameters:
          config:
            type: Config
        returns:
          type: dict[str, object]
        """
        return {}


@public
@typechecked
def plugin_context(config: Config) -> dict[str, object]:
    """
    title: Load only explicitly configured entry points and validate results.
    parameters:
      config:
        type: Config
    returns:
      type: dict[str, object]
    """
    available = {
        entry.name: entry for entry in entry_points(group='doukimd.plugins')
    }
    context: dict[str, object] = {}
    for name in config.plugins:
        if name not in available:
            raise BuildError('plugins', f'Plugin is not installed: {name}')
        manager = pluggy.PluginManager('doukimd')
        manager.add_hookspecs(ContextHooks)
        try:
            manager.register(available[name].load(), name=name)
            manager.check_pending()
            results = cast(
                list[object], manager.hook.doukimd_context(config=config)
            )
            if len(results) != 1:
                raise BuildError(
                    'plugins', f'{name} must provide doukimd_context'
                )
            context[name] = TypeAdapter(dict[str, JsonValue]).validate_python(
                results[0], strict=True
            )
        except (
            ValueError,
            TypeError,
            ValidationError,
            pluggy.PluginValidationError,
        ) as error:
            raise BuildError('plugins', f'{name}: {error}') from error
    return context
