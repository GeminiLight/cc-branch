from __future__ import annotations


def render_template(template: str | None, context: dict[str, object]) -> str:
    if not template:
        return ""

    rendered = template
    for key, value in context.items():
        text = str(value)
        rendered = rendered.replace("{{" + key + "}}", text)
        rendered = rendered.replace("{" + key + "}", text)
    return rendered
