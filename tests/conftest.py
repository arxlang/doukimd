"""
title: Reusable integration projects.
"""

from __future__ import annotations

import shutil

from pathlib import Path

import pytest

from doukimd.runtime import typechecked


@pytest.fixture
@typechecked
def project(tmp_path: Path) -> Path:
    """
    title: Create a minimal documentation project.
    parameters:
      tmp_path:
        type: Path
    returns:
      type: Path
    """
    (tmp_path / 'doukimd.yaml').write_text(
        'site:\n  title: Test docs\nproject:\n  name: test\n',
        encoding='utf-8',
    )
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs/index.md').write_text('# Home\n', encoding='utf-8')
    return tmp_path


@pytest.fixture
@typechecked
def example(tmp_path: Path) -> Path:
    """
    title: Copy the runnable example without build output.
    parameters:
      tmp_path:
        type: Path
    returns:
      type: Path
    """
    source = Path(__file__).parents[1] / 'examples/basic'
    shutil.copytree(
        source,
        tmp_path,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('build', '__pycache__'),
    )
    return tmp_path
