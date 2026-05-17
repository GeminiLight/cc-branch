from __future__ import annotations

from ..runtime.shells import tmux_install_hint
from ..text import count_label


def _get_install_suggestion(agent_name: str, command: str) -> str:
    suggestions = {
        "claude": "Install Claude Code: https://docs.anthropic.com/claude/docs/claude-code",
        "codex": "Install Codex: npm install -g @openai/codex-cli",
        "gemini": "Install Gemini CLI: pip install google-generativeai-cli",
        "cursor": "Install Cursor CLI: https://cursor.sh/cli",
        "kimi": "Install Kimi CLI: pip install kimi-cli",
    }
    for key, suggestion in suggestions.items():
        if key in agent_name.lower() or key in command.lower():
            return suggestion
    return f"Make sure '{command}' is installed and in your PATH"


def _get_fix_suggestion(issue_type: str, context: dict) -> str:
    suggestions = {
        "duplicate_tmux_session": "Rename one of the slots to avoid tmux session name collision",
        "duplicate_slot": f"Rename duplicate slot '{context.get('slot', 'unknown')}'",
        "duplicate_window": f"Rename duplicate window in slot '{context.get('slot', 'unknown')}'",
        "reserved_name_separator": "Rename it using letters, numbers, hyphens, or underscores; ':' and '.' are reserved for targets",
        "unknown_agent": f"Add agent '{context.get('agent', 'unknown')}' to the 'agents' section in your config",
        "missing_session_id": "Run: cc-branch plan --write-state",
        "missing_command": f"Install the required command: {context.get('command', 'unknown')}",
        "invalid_env_key": f"Fix environment variable name '{context.get('key', 'unknown')}' (must start with letter/underscore)",
        "missing_cwd": f"Create directory: mkdir -p {context.get('cwd', 'unknown')}",
        "missing_launch_command": "Add a 'command' or 'agent' to this window",
        "missing_tmux": tmux_install_hint(),
        "orphaned_state": "Run: cc-branch session prune",
    }
    return suggestions.get(issue_type, "Check your configuration")


def _describe_issue(issue_type: str, context: dict) -> str:
    if issue_type == "duplicate_tmux_session":
        return f"duplicate tmux session '{context.get('session', 'unknown')}'"
    if issue_type == "duplicate_slot":
        return f"duplicate slot '{context.get('slot', 'unknown')}'"
    if issue_type == "duplicate_window":
        return f"duplicate window '{context.get('window', 'unknown')}'"
    if issue_type == "reserved_name_separator":
        scope = context.get("scope", "name")
        name = context.get("name", "unknown")
        return f"{scope} name '{name}' uses reserved target separator"
    if issue_type == "unknown_agent":
        return f"unknown agent '{context.get('agent', 'unknown')}'"
    if issue_type == "missing_session_id":
        return "missing session_id"
    if issue_type == "missing_command":
        return f"missing command '{context.get('command', 'unknown')}'"
    if issue_type == "invalid_env_key":
        return f"invalid env key '{context.get('key', 'unknown')}'"
    if issue_type == "missing_cwd":
        return f"missing cwd '{context.get('cwd', 'unknown')}'"
    if issue_type == "missing_launch_command":
        return "missing launch command"
    if issue_type == "missing_tmux":
        return "missing tmux"
    if issue_type == "orphaned_state":
        return count_label(int(context.get("count", 0) or 0), "stale local session record")
    return issue_type.replace("_", " ")
