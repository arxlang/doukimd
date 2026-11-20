"""
title: Release transport retries and recovery of already tagged versions.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

from pathlib import Path

import pytest

from doukimd.runtime import typechecked

pytestmark = pytest.mark.skipif(
    os.name == 'nt', reason='The release workflow runs Bash scripts on Ubuntu'
)
SCRIPTS = Path(__file__).resolve().parents[1] / '.github/scripts'


@typechecked
def executable(path: Path, content: str) -> None:
    """
    title: Create an executable stand-in for an external release service.
    parameters:
      path: Temporary command path.
      content: Script body to execute with the current Python interpreter.
    """
    path.write_text(f'#!{sys.executable}\n{content}', encoding='utf-8')
    path.chmod(0o755)


@pytest.mark.parametrize(
    ('notes', 'failures', 'attempts', 'status'),
    [(True, 2, 3, 0), (True, 99, 3, 7), (False, 2, 1, 7)],
)
@typechecked
def test_git_retries_only_release_notes(
    tmp_path: Path, notes: bool, failures: int, attempts: int, status: int
) -> None:
    """
    title: Retry notes pushes without changing arguments or masking failure.
    parameters:
      tmp_path: Temporary transport fixture directory.
      notes: Whether to push release notes or a regular branch.
      failures: Number of failures before the transport succeeds.
      attempts: Expected transport invocations.
      status: Expected command exit status.
    """
    state = tmp_path / 'calls.json'
    transport = tmp_path / 'transport'
    executable(
        transport,
        'import json, os, sys\nfrom pathlib import Path\n'
        'path = Path(os.environ["CALLS"])\n'
        'calls = json.loads(path.read_text()) if path.exists() else []\n'
        'calls.append(sys.argv[1:])\n'
        'path.write_text(json.dumps(calls))\n'
        'sys.exit(7 if len(calls) <= int(os.environ["FAILURES"]) else 0)\n',
    )
    executable(tmp_path / 'sleep', '')
    route = 'refs/notes/semantic-release-1.4.8' if notes else 'HEAD:main'
    args = ['push', '--', 'https://example.invalid/repo with spaces', route]
    result = subprocess.run(
        ['bash', str(SCRIPTS / 'release-bin/git'), *args],
        env={
            **os.environ,
            'PATH': f'{tmp_path}{os.pathsep}{os.environ["PATH"]}',
            'DOUKIMD_RELEASE_GIT': str(transport),
            'CALLS': str(state),
            'FAILURES': str(failures),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == status, result.stderr
    assert json.loads(state.read_text()) == [args] * attempts


@typechecked
def git_command(directory: Path, *args: str) -> str:
    """
    title: Execute Git against an isolated fixture repository.
    parameters:
      directory: Fixture working directory.
      args:
        variadic: positional
        description: Git arguments without shell interpolation.
    returns: Stripped command output.
    """
    return subprocess.run(
        ['git', *args],
        cwd=directory,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
@typechecked
def recovery(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """
    title: Create a real tagged Git remote and simulated publication services.
    parameters:
      tmp_path: Temporary root for repositories and service state.
    returns: Tagged repository and environment for release recovery.
    """
    remote = tmp_path / 'remote'
    remote.mkdir()
    git_command(remote, 'init', '--bare')
    source = tmp_path / 'source'
    source.mkdir()
    git_command(source, 'init', '--initial-branch=main')
    git_command(source, 'config', 'user.name', 'Release fixture')
    git_command(source, 'config', 'user.email', 'release@example.invalid')
    (source / 'pyproject.toml').write_text('version = "1.4.8"\n')
    (source / 'marker').write_text('tagged source')
    (source / 'docs').mkdir()
    (source / 'docs/changelog.md').write_text(
        '# Release Notes\n\n## [1.4.8](url)\n\nMemory fix.\n\n'
        '## [1.4.7](url)\n\nPrevious notes.\n'
    )
    git_command(source, 'add', '.')
    git_command(source, 'commit', '-m', 'chore(release): 1.4.8')
    git_command(source, 'tag', '1.4.8')
    git_command(source, 'tag', '1.4.9')
    unrelated = git_command(
        source, 'commit-tree', 'HEAD^{tree}', '-m', 'Unrelated release'
    )
    git_command(source, 'tag', '2.0.0', unrelated)
    git_command(source, 'remote', 'add', 'origin', str(remote))
    git_command(source, 'push', '--tags', 'origin', 'main')
    (source / 'marker').write_text('unreleased working tree')

    commands = tmp_path / 'commands'
    commands.mkdir()
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    state = tmp_path / 'service.json'
    state.write_text(
        json.dumps(
            {'release': False, 'assets': [], 'uploads': [], 'calls': []}
        )
    )
    stub = (
        'import json, os, re, sys\nfrom pathlib import Path\n'
        'path = Path(os.environ["SERVICE_STATE"])\n'
        'state = json.loads(path.read_text())\n'
        'tool, args = Path(sys.argv[0]).name, sys.argv[1:]\n'
        'state["calls"].append([tool, *args])\n'
        'status = 0\n'
        'if tool == "poetry":\n'
        ' if args == ["version", "--short"]:\n'
        '  print(re.search(r\'version = "(.*)"\', '
        'Path("pyproject.toml").read_text())[1])\n'
        ' elif args == ["build"]:\n'
        '  assert Path("marker").read_text() == "tagged source"\n'
        '  Path("dist").mkdir()\n'
        '  Path("dist/doukimd-1.4.8.whl").write_bytes(b"wheel")\n'
        '  Path("dist/doukimd-1.4.8.tar.gz").write_bytes(b"sdist")\n'
        ' elif args == ["publish", "--skip-existing", "--no-interaction"]:\n'
        '  state["uploads"] = ["wheel", "sdist"]\n'
        '  status = int(os.environ.get("PUBLISH_STATUS", "0"))\n'
        ' else: raise AssertionError(args)\n'
        'elif tool == "gh":\n'
        ' if args[:2] == ["release", "view"]:\n'
        '  status = 0 if state["release"] else 1\n'
        '  if "--json" in args: print("\\n".join(state["assets"]))\n'
        ' elif args[:2] == ["release", "create"]:\n'
        '  assert not state["release"]\n'
        '  state["release"] = True\n'
        '  state["notes"] = Path(args[args.index("--notes-file") + 1])'
        '.read_text()\n'
        ' elif args[:2] == ["release", "upload"]:\n'
        '  name = Path(args[3]).name\n'
        '  assert name not in state["assets"]\n'
        '  if name == os.environ.get("FAIL_ASSET"): status = 5\n'
        '  else: state["assets"].append(name)\n'
        ' else: raise AssertionError(args)\n'
        'path.write_text(json.dumps(state))\n'
        'sys.exit(status)\n'
    )
    for name in ['poetry', 'gh']:
        executable(commands / name, stub)
    environment = {
        **os.environ,
        'PATH': os.pathsep.join(
            [str(SCRIPTS / 'release-bin'), str(commands), os.environ['PATH']]
        ),
        'DOUKIMD_RELEASE_GIT': str(shutil.which('git')),
        'RUNNER_TEMP': str(runtime),
        'GITHUB_REPOSITORY': 'arxlang/doukimd',
        'GITHUB_OUTPUT': str(tmp_path / 'output'),
        'SERVICE_STATE': str(state),
    }
    return source, environment


@typechecked
def test_recover_tagged_release_is_repeatable(
    recovery: tuple[Path, dict[str, str]],
) -> None:
    """
    title: Publish the exact tagged source and safely repeat partial recovery.
    parameters:
      recovery: Local tagged remote and simulated publication services.
    """
    source, environment = recovery
    interrupted = subprocess.run(
        ['bash', str(SCRIPTS / 'resume-release.sh'), '1.4.8'],
        cwd=source,
        env={**environment, 'FAIL_ASSET': 'doukimd-1.4.8.tar.gz'},
        capture_output=True,
        text=True,
        check=False,
    )
    assert interrupted.returncode == 5, interrupted.stderr
    assert not Path(environment['GITHUB_OUTPUT']).exists()
    for _ in range(2):
        subprocess.run(
            ['bash', str(SCRIPTS / 'resume-release.sh'), '1.4.8'],
            cwd=source,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
    state = json.loads(Path(environment['SERVICE_STATE']).read_text())
    assert state['uploads'] == ['wheel', 'sdist']
    assert state['assets'] == ['doukimd-1.4.8.whl', 'doukimd-1.4.8.tar.gz']
    assert 'Memory fix.' in state['notes']
    assert 'Previous notes.' not in state['notes']
    assert (
        Path(environment['GITHUB_OUTPUT']).read_text().splitlines()
        == ['source_ref=' + git_command(source, 'rev-parse', '1.4.8')] * 2
    )
    assert 'semantic-release-1.4.8' in git_command(
        source, 'ls-remote', 'origin', 'refs/notes/*'
    )
    assert not list(Path(environment['RUNNER_TEMP']).iterdir())
    assert (source / 'marker').read_text() == 'unreleased working tree'


@pytest.mark.parametrize('tag', ['main', '1.4.9', '9.9.9', '2.0.0'])
@typechecked
def test_recovery_rejects_invalid_tags(
    recovery: tuple[Path, dict[str, str]], tag: str
) -> None:
    """
    title: Refuse unknown tags and package version mismatches before publish.
    parameters:
      recovery: Local tagged remote and simulated publication services.
      tag: Invalid recovery input.
    """
    source, environment = recovery
    result = subprocess.run(
        ['bash', str(SCRIPTS / 'resume-release.sh'), tag],
        cwd=source,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    state = json.loads(Path(environment['SERVICE_STATE']).read_text())
    assert not state['uploads']
    assert not state['release']
    assert not Path(environment['GITHUB_OUTPUT']).exists()
    assert not list(Path(environment['RUNNER_TEMP']).iterdir())


@typechecked
def test_recovery_does_not_mark_failed_publication_successful(
    recovery: tuple[Path, dict[str, str]],
) -> None:
    """
    title: Keep documentation gated when package publication fails.
    parameters:
      recovery: Local tagged remote and simulated publication services.
    """
    source, environment = recovery
    result = subprocess.run(
        ['bash', str(SCRIPTS / 'resume-release.sh'), '1.4.8'],
        cwd=source,
        env={**environment, 'PUBLISH_STATUS': '4'},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4
    state = json.loads(Path(environment['SERVICE_STATE']).read_text())
    assert not state['release']
    assert not Path(environment['GITHUB_OUTPUT']).exists()
    assert not list(Path(environment['RUNNER_TEMP']).iterdir())
