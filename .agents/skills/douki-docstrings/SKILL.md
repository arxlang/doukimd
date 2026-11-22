---
name: douki-docstrings
description:
  Write, validate, and minimally maintain Douki 0.14+ annotation-first Python
  docstrings and generated DoukiMD API documentation.
---

# Maintain Douki annotation-first source contracts

**Use for public Python symbols or generated API documentation.** Apply
[minimal-change](../minimal-change/SKILL.md).

## Annotation-first format

Python annotations hold types. YAML docstrings hold prose and metadata. Legacy
YAML `type:` fields are rejected by the shipped Douki schema.

For example:

```python
def add(left: int, right: int = 0) -> int:
    """
    title: Add two integers.
    parameters:
      left:
        description: First addend.
      right:
        description: Optional second addend.
    returns:
      description: Sum of the two integers.
    """
    return left + right
```

In `examples/basic/src/example.py`, preserve the same structure. Documentation
must describe behavior without duplicating annotations.

## Source contracts and validation

- Read and validate the schema shipped by Douki; never fork or import private
  schema modules.
- Never Jinja-expand docstrings or execute source during collection.
- Never rewrite source or generated API prose during a build.
- Update a docstring only when signature, behavior, parameters, returns,
  attributes, or safety contracts change.

Verify:

```bash
poetry run douki check src tests examples/basic/src
```

Use `douki sync` only when explicit synchronization has been requested:

```bash
poetry run douki sync src tests examples/basic/src
```

For generated references, update source docstrings and regenerate documentation;
do not hand-maintain API prose.
