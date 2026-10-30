"""
title: Read version four notebooks without importing kernels or running code.
"""

from __future__ import annotations

import json

from pathlib import Path

import nbformat

from jsonschema.exceptions import ValidationError as SchemaError
from public import public
from pydantic import TypeAdapter

from doukimd.errors import BuildError
from doukimd.notebook_models import Notebook
from doukimd.runtime import typechecked


@public
@typechecked
def notebook_text(value: str | list[str]) -> str:
    """
    title: Join the two multiline string encodings allowed by nbformat.
    parameters:
      value:
        type: str | list[str]
    returns:
      type: str
    """
    return value if isinstance(value, str) else ''.join(value)


@public
@typechecked
def load_notebook(path: Path) -> Notebook:
    """
    title: Validate the original document before projecting rendering fields.
    parameters:
      path:
        type: Path
    returns:
      type: Notebook
    """
    try:
        raw: object = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw, dict) or raw.get('nbformat') != 4:
            raise BuildError(
                'notebook', 'Only nbformat version 4 is supported', path
            )
        minor = raw.get('nbformat_minor')
        if type(minor) is not int or minor > nbformat.current_nbformat_minor:
            raise BuildError(
                'notebook', 'Unsupported nbformat minor version', path
            )
        # validate does not normalize, repair, convert, or persist notebooks.
        nbformat.validate(raw)
        return TypeAdapter(Notebook).validate_python(raw)
    except SchemaError as error:
        location = '.'.join(str(part) for part in error.absolute_path)
        raise BuildError(
            'notebook', f'{location or "document"}: {error.message}', path
        ) from error
    except (OSError, UnicodeError, ValueError) as error:
        raise BuildError('notebook', str(error), path) from error
