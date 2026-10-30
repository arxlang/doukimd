"""
title: Typed projections of validated notebook cells and saved outputs.
"""

from __future__ import annotations

from typing import Annotated, Literal

from public import public
from pydantic import BaseModel, ConfigDict, Field, JsonValue


@public
class NotebookValue(BaseModel):
    """
    title: Project relevant fields after validation against nbformat's schema.
    """

    model_config = ConfigDict(strict=True, extra='ignore')


@public
class CellMetadata(NotebookValue):
    """
    title: Standard cell tags that control published input and output.
    attributes:
      tags:
        type: list[str]
    """

    tags: list[str] = Field(default_factory=list)


@public
class StreamOutput(NotebookValue):
    """
    title: Saved stdout or stderr from a code cell.
    attributes:
      output_type:
        type: Literal[stream]
      name:
        type: Literal[stdout, stderr]
      text:
        type: str | list[str]
    """

    output_type: Literal['stream']
    name: Literal['stdout', 'stderr']
    text: str | list[str]


@public
class ErrorOutput(NotebookValue):
    """
    title: A recorded exception rendered without executing its traceback.
    attributes:
      output_type:
        type: Literal[error]
      ename:
        type: str
      evalue:
        type: str
      traceback:
        type: list[str]
    """

    output_type: Literal['error']
    ename: str
    evalue: str
    traceback: list[str]


@public
class RichOutput(NotebookValue):
    """
    title: A display or expression result containing alternative MIME formats.
    attributes:
      output_type:
        type: Literal[display_data, execute_result]
      data:
        type: dict[str, JsonValue]
    """

    output_type: Literal['display_data', 'execute_result']
    data: dict[str, JsonValue]


NotebookOutput = Annotated[
    StreamOutput | ErrorOutput | RichOutput, Field(discriminator='output_type')
]


@public
class MarkdownCell(NotebookValue):
    """
    title: Markdown prose with optional embedded image attachments.
    attributes:
      cell_type:
        type: Literal[markdown]
      source:
        type: str | list[str]
      metadata:
        type: CellMetadata
      attachments:
        type: dict[str, dict[str, JsonValue]]
    """

    cell_type: Literal['markdown']
    source: str | list[str]
    metadata: CellMetadata = Field(default_factory=CellMetadata)
    attachments: dict[str, dict[str, JsonValue]] = Field(default_factory=dict)


@public
class CodeCell(NotebookValue):
    """
    title: Literal code and its existing outputs.
    attributes:
      cell_type:
        type: Literal[code]
      source:
        type: str | list[str]
      metadata:
        type: CellMetadata
      execution_count:
        type: int | None
      outputs:
        type: list[NotebookOutput]
    """

    cell_type: Literal['code']
    source: str | list[str]
    metadata: CellMetadata = Field(default_factory=CellMetadata)
    execution_count: int | None
    outputs: list[NotebookOutput]


@public
class RawCell(NotebookValue):
    """
    title: Raw notebook cells retained as escaped text.
    attributes:
      cell_type:
        type: Literal[raw]
      source:
        type: str | list[str]
      metadata:
        type: CellMetadata
    """

    cell_type: Literal['raw']
    source: str | list[str]
    metadata: CellMetadata = Field(default_factory=CellMetadata)


NotebookCell = Annotated[
    MarkdownCell | CodeCell | RawCell, Field(discriminator='cell_type')
]


@public
class Notebook(NotebookValue):
    """
    title: A nonexecuting projection of a version four notebook.
    attributes:
      nbformat:
        type: Literal[4]
      nbformat_minor:
        type: int
      metadata:
        type: dict[str, JsonValue]
      cells:
        type: list[NotebookCell]
    """

    nbformat: Literal[4]
    nbformat_minor: int
    metadata: dict[str, JsonValue]
    cells: list[NotebookCell]
