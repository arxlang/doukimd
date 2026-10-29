# Contributing

Use Python 3.10–3.14 and Poetry 2:

```console
poetry install
poetry run pre-commit install
poetry run makim all.ci
poetry check --lock
```

Update dependencies using `poetry lock`, never by editing the lockfile.
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
