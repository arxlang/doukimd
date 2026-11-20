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
        description: Notebook tags controlling cell presentation.
    """

    tags: list[str] = Field(default_factory=list)


@public
class StreamOutput(NotebookValue):
    """
    title: Saved stdout or stderr from a code cell.
    attributes:
      output_type:
        description: Notebook output representation to validate.
      name:
        description: Name used to identify the requested item.
      text:
        description: Text content to process.
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
        description: Notebook output representation to validate.
      ename:
        description: Recorded notebook exception class name.
      evalue:
        description: Recorded notebook exception message.
      traceback:
        description: Saved traceback lines from notebook execution.
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
        description: Notebook output representation to validate.
      data:
        description: Structured content or template data to process.
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
        description: Notebook cell representation to validate.
      source:
        description: Source content or configured API source name.
      metadata:
        description: Literal metadata associated with this document.
      attachments:
        description: Inline notebook attachments keyed by their local names.
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
        description: Notebook cell representation to validate.
      source:
        description: Source content or configured API source name.
      metadata:
        description: Literal metadata associated with this document.
      execution_count:
        description: Saved notebook execution count; no code is executed.
      outputs:
        description: Saved notebook outputs in their recorded order.
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
        description: Notebook cell representation to validate.
      source:
        description: Source content or configured API source name.
      metadata:
        description: Literal metadata associated with this document.
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
        description: Notebook format major version.
      nbformat_minor:
        description: Notebook format minor version.
      metadata:
        description: Literal metadata associated with this document.
      cells:
        description: Notebook cells in their original order.
    """

    nbformat: Literal[4]
    nbformat_minor: int
    metadata: dict[str, JsonValue]
    cells: list[NotebookCell]
