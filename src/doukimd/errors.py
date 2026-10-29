"""
title: Structured build errors.
"""

from __future__ import annotations

from pathlib import Path

from public import public

from doukimd.runtime import typechecked


@public
@typechecked
class BuildError(Exception):
    """
    title: Describe a failure in a named documentation phase.
    attributes:
      phase:
        type: str
      message:
        type: str
      source:
        type: Path | None
    """

    phase: str
    message: str
    source: Path | None

    def __init__(
        self, phase: str, message: str, source: Path | None = None
    ) -> None:
        """
        title: Initialize a diagnostic without inventing a source location.
        parameters:
          phase:
            type: str
          message:
            type: str
          source:
            type: Path | None
        """
        self.phase = phase
        self.message = message
        self.source = source
        location = f'{source}: ' if source is not None else ''
        super().__init__(f'{location}[{phase}] {message}')
