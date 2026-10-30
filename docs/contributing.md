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
