"""
title: Lazy published artifacts and build result validation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doukimd.models import SiteBuild
from doukimd.output import PublishedFiles
from doukimd.runtime import typechecked


@typechecked
def test_published_result_reads_only_requested_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    title: Construct and inspect a result without eagerly reading its files.
    parameters:
      tmp_path:
        description: Temporary published output directory.
      monkeypatch:
        description: Fixture restoring patched filesystem methods.
    """
    (tmp_path / 'index.html').write_bytes(b'home')
    (tmp_path / 'other.html').write_bytes(b'other')
    reads: list[Path] = []
    read_bytes = Path.read_bytes

    @typechecked
    def read(path: Path) -> bytes:
        """
        title: Track disk reads while constructing and querying the result.
        parameters:
          path:
            description: Requested artifact path.
        returns:
          description: File contents read from disk.
        """
        reads.append(path)
        return read_bytes(path)

    monkeypatch.setattr(Path, 'read_bytes', read)
    files = PublishedFiles(tmp_path, ('index.html', 'other.html'))
    result = SiteBuild(files, 2)
    assert result.files is files
    assert len(result.files) == 2
    assert list(result.files) == ['index.html', 'other.html']
    assert 'index.html' in result.files
    assert 'missing.html' not in result.files
    with pytest.raises(KeyError):
        result.files['../outside.html']
    assert reads == []
    assert result.files['index.html'] == b'home'
    assert reads == [tmp_path / 'index.html']
    (tmp_path / 'index.html').write_bytes(b'changed')
    assert result.files['index.html'] == b'changed'
