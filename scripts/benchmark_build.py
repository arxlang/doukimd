"""
title: Measure complete site compilation without writing build output.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import tempfile
import time

from importlib.metadata import version
from pathlib import Path

from public import private

from doukimd.build import compile_site
from doukimd.runtime import typechecked


@private
@typechecked
def synthetic_project(root: Path) -> Path:
    """
    title: Generate forty modules with twenty public callables each.
    parameters:
      root:
        type: Path
    returns:
      type: Path
    """
    docs = root / 'docs'
    docs.mkdir()
    (docs / 'index.md').write_text('# Home\n', encoding='utf-8')
    source = root / 'src/package'
    source.mkdir(parents=True)
    (source / '__init__.py').write_text(
        '"""title: Package."""\n', encoding='utf-8'
    )
    for module in range(40):
        (source / f'module_{module}.py').write_text(
            '"""title: Module."""\n'
            + ''.join(
                f'def function_{member}() -> None:\n'
                f'    """title: Function {member}."""\n'
                for member in range(20)
            ),
            encoding='utf-8',
        )
    config = root / 'doukimd.yaml'
    config.write_text(
        'site:\n  title: Benchmark\nproject:\n  name: benchmark\n'
        'api:\n  sources:\n    - language: python\n'
        '      root: src\n      modules: [package]\n',
        encoding='utf-8',
    )
    return config


@private
@typechecked
def main() -> None:
    """
    title: Report complete build timings and workload size as JSON.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'config',
        type=Path,
        nargs='?',
        help='default: synthetic 40-module site',
    )
    parser.add_argument('--repeat', type=int, default=3)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error('--repeat must be positive')
    with tempfile.TemporaryDirectory(prefix='doukimd-benchmark-') as directory:
        config = args.config or synthetic_project(Path(directory))
        measure(config, args.repeat)


@private
@typechecked
def measure(config: Path, repeat: int) -> None:
    """
    title: Time the same complete workload repeatedly without retaining output.
    parameters:
      config:
        type: Path
      repeat:
        type: int
    """
    timings: list[float] = []
    for _ in range(repeat):
        started = time.perf_counter()
        result = compile_site(config)
        timings.append(time.perf_counter() - started)
        print(
            json.dumps(
                {
                    'seconds': timings[-1],
                    'median_seconds': statistics.median(timings),
                    'pages': result.page_count,
                    'output_bytes': sum(map(len, result.files.values())),
                    'python': platform.python_version(),
                    'douki': version('douki'),
                },
                sort_keys=True,
            ),
            flush=True,
        )
        del result


if __name__ == '__main__':
    main()
