from __future__ import annotations

from collections.abc import Mapping


def render_template(template: str | None, context: Mapping[str, object]) -> str:
    if not template:
        return ""

    rendered = template
    for key, value in context.items():
        text = str(value)
        rendered = rendered.replace("{{" + key + "}}", text)
        rendered = rendered.replace("{" + key + "}", text)
    return rendered
