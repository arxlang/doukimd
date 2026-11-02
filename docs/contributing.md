# Contributing

Use Python 3.10–3.14 and Poetry 2:

```console
poetry install
poetry run pre-commit install
poetry run makim all.ci
poetry check --lock
```

Update dependencies using `poetry lock`, never by editing the lockfile.
Frontend preference checks use Node 24 without npm dependencies:
`node tests/theme.cjs src/doukimd/themes/default/theme.js`.
CI runs them separately; pytest also runs them when Node is installed.
Douki docstrings must be synchronized and idempotent:

```console
poetry run douki sync src tests examples/basic/src
poetry run douki check src tests examples/basic/src
```

The Makim groups, hooks, and release configuration are adapted from
[Douki](https://github.com/arxlang/douki), commit
`f77adee49546d4ea8e95ced671d470379c5bd741`.
The BSD license and upstream attribution are retained. Documentation is built
with DoukiMD. Publication is never triggered by pull requests.

## Benchmark builds

Measure complete in-memory compilation, including API collection, link
validation, HTML rendering, and search indexing:

```console
poetry run python scripts/benchmark_build.py
poetry run python scripts/benchmark_build.py /path/to/arx/doukimd.yaml
```

The default workload generates 40 modules with 20 callables each in a
temporary directory. Each command reports three timings, their running
median, page count, output size, Python version, and Douki version as JSON.
It does not write site output. Compare the same workload and dependency
environment; keep Douki pinned to `0.13.0` in both runs.

To compare an older source revision without changing the working checkout:

```console
snapshot=$(mktemp -d)
git archive <revision> src/doukimd | tar -x -C "$snapshot"
PYTHONPATH="$snapshot/src" poetry run python scripts/benchmark_build.py
```

On Python 3.12.14, the 843-page default workload took 105.1 seconds with
DoukiMD 1.4.0 (one run), versus a 4.6-second median here (three runs).
The full Arx site at `e05b7d59409c47c993b5ac878578568bfa86789c` generated
8,526 pages: upstream `fecab8b` took 221.6 seconds, versus 85.4 seconds here
(one run each). These are local compilation measurements, excluding process
startup and disk publication, rather than a CI timing guarantee.

## Publish the documentation

After a successful package release, the **Release** workflow calls the
**Documentation** workflow with the exact release commit. The site is built
after publication, so its version badge and changelog match the released
version, and published to `gh-pages`. Failed releases, dry runs, and runs
without a new version do not trigger this deployment.

For documentation-only changes, run **Documentation** manually from upstream
`main`. It builds the site and publishes the `documentation` artifact to the
same `gh-pages` branch. Push and pull-request runs only build and validate
documentation. Both publication paths share the deployment concurrency group.

After the first publication creates `gh-pages`, configure **Settings → Pages**
to **Deploy from a branch**, selecting `gh-pages` and **/ (root)**.
The publishing action adds `.nojekyll` for the generated static site.
