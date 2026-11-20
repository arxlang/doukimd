"""
title: Read published build artifacts without retaining their contents.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path, PurePosixPath

from public import public

from doukimd.runtime import typechecked


@public
@typechecked
class PublishedFiles(Mapping[str, bytes]):
    """
    title: A read-only view of files in a published output directory.
    attributes:
      directory:
        description: Published directory read when an artifact is requested.
      routes:
        description: Relative file destinations produced by the build.
    """

    directory: Path
    routes: dict[str, None]

    def __init__(self, directory: Path, routes: tuple[str, ...]) -> None:
        """
        title: Retain destinations without opening any generated files.
        parameters:
          directory:
            description: Published output directory.
          routes:
            description: Relative file destinations produced by the build.
        """
        self.directory = directory
        self.routes = dict.fromkeys(routes)

    def __getitem__(self, route: str) -> bytes:
        """
        title: Read one requested artifact from the current output directory.
        parameters:
          route:
            description: Relative destination of a generated file.
        returns:
          description: Artifact bytes read without caching.
        """
        if route not in self.routes:
            raise KeyError(route)
        return self.directory.joinpath(
            *PurePosixPath(route).parts
        ).read_bytes()

    def __iter__(self) -> Iterator[str]:
        """
        title: Iterate generated destinations without reading file contents.
        returns:
          description: Iterator over relative artifact destinations.
        """
        return iter(self.routes)

    def __len__(self) -> int:
        """
        title: Count destinations without reading file contents.
        returns:
          description: Number of generated artifacts.
        """
        return len(self.routes)

    def __contains__(self, route: object) -> bool:
        """
        title: Check destination membership without opening an artifact.
        parameters:
          route:
            description: Candidate artifact destination.
        returns:
          description: Whether the build produced the destination.
        """
        return route in self.routes
