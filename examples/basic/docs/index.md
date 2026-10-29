---
title: Example project
render: jinja
meta:
  audience: Library users
---

Documentation for **{{ page.meta.audience | md_text }}**.

{% include "install.md.jinja" %}

{% for target in data.support.targets %}
- {{ target.name | md_text }}: {{ target.status | md_text }}
{% endfor %}

Read the {@api python:example.add} reference.

::: api python:example.add
show_source: true
:::

[Plain Markdown](plain.md#literal-templates)
