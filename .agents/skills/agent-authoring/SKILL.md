---
name: agent-authoring
description:
  Create or maintain portable DoukiMD Agent Skills in `.agents/skills`, with
  narrow triggers, minimal duplication, verified repository facts and safe
  permissions.
---

# Create and maintain effective DoukiMD skills

**Use for adding or revising `.agents/skills/**/SKILL.md`.** Do not create
platform-specific Copilot configuration. Apply
[minimal-change](../minimal-change/SKILL.md).

## What a good skill contains

- YAML frontmatter whose `name` exactly matches the directory name.
- A description that states both the work and its trigger.
- Verified paths and commands from `pyproject.toml`, `.makim.yaml`,
  `.pre-commit-config.yaml`, `src/doukimd/`, `tests/`, examples, and workflows.
- Preconditions, decision points, validation, failure paths, stop conditions,
  and explicit mutation permissions.
- Only relative links that resolve inside `.agents/skills/`.

## Authoring procedure

1. Inspect the smallest relevant implementation, tests, and canonical task.
2. Read `AGENTS.md` and existing skills before duplicating a procedure.
3. Adapt every command and path to DoukiMD. Remove compiler, native, monorepo,
   and Arx-specific concepts.
4. Ground API and implementation work in the four-stage pipeline:
   config/models → static collection/API extraction → content/reference/
   navigation/search rendering → theme/assets/plugins/output.
5. Preserve the safety boundaries: no source imports, no notebook execution,
   no Jinja evaluation of docstrings, and no silently dropped unsupported input.
6. Review stale paths, secret exposure, broad permissions, and unauthorized
   remote mutation.
7. Validate frontmatter names, relative links, LF endings, and formatting.

**Exit:** a skill produces a verifiable contribution workflow without
duplicating repository-wide rules or adding platform-specific discovery.
