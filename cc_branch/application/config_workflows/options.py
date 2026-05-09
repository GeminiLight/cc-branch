"""Config metadata option workflows."""

from __future__ import annotations

from pathlib import Path

from ..results import ActionResult


def profile_options() -> ActionResult:
    """Return available starter profiles for UI clients."""
    import cc_branch.application.config_workflows as workflows

    return ActionResult(
        ok=True,
        code="profiles_loaded",
        message="Profiles loaded",
        payload={
            "profiles": [
                {"id": profile, "description": workflows.get_profile_description(profile)}
                for profile in workflows.get_available_profiles()
            ]
        },
    )


def opener_options(config_path: Path) -> ActionResult:
    """Return available openers, applying workspace custom opener defaults when present."""
    import cc_branch.application.config_workflows as workflows

    if config_path.exists():
        workspace = workflows.load_workspace(config_path)
        payload = workflows.list_openers(
            workspace.default_opener or "auto-terminal",
            workspace.openers,
        )
    else:
        payload = workflows.list_openers()
    return ActionResult(ok=True, code="openers_loaded", message="Openers loaded", payload=payload)


def agent_options(config_path: Path) -> ActionResult:
    """Return effective agent definitions for a workspace or registry fallback."""
    import cc_branch.application.config_workflows as workflows

    if config_path.exists():
        workspace = workflows.load_workspace(config_path)
        agents = workspace.agents
    else:
        project_dir = workflows.project_dir_for_config(config_path)
        agents = {
            name: definition.to_agent_spec()
            for name, definition in workflows.load_agent_registry(cwd=project_dir).items()
        }
    return ActionResult(
        ok=True,
        code="agents_loaded",
        message="Agents loaded",
        payload={"agents": [agent_payload(name, spec) for name, spec in sorted(agents.items())]},
    )


def agent_payload(name: str, spec) -> dict:
    """Return one serializable agent option payload."""
    if hasattr(spec, "to_dict"):
        data = spec.to_dict()
    elif hasattr(spec, "__dict__"):
        data = dict(spec.__dict__)
    else:
        data = dict(spec)
    return {"id": name, **data}
