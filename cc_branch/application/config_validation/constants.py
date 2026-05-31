"""Raw workspace config validation constants."""

from __future__ import annotations

from ...runtime.capabilities import RUNTIME_CAPABILITIES

TOP_LEVEL_FIELDS = {
    "version",
    "project",
    "root",
    "display",
    "agents",
    "openers",
    "openWith",
    "layoutBackend",
    "defaults",
    "tabs",
}
DISPLAY_FIELDS = {"mode", "columns", "dashboard"}
DEFAULTS_FIELDS = {"shell"}
REMOTE_FIELDS = {"host", "user", "port", "cwd", "args", "options"}
AGENT_FIELDS = {
    "command",
    "resume_mode",
    "resume_template",
    "create_mode",
    "create_template",
    "label_template",
    "label_mode",
    "rename_template",
}
OPENER_FIELDS = {"label", "kind", "command", "args", "capabilities"}
TAB_FIELDS = {"name", "layout", "layoutBackend", "opener", "cwd", "env", "remote", "panes"}
PANE_FIELDS = {
    "name",
    "layoutBackend",
    "layout",
    "opener",
    "cwd",
    "env",
    "remote",
    "windows",
    "command",
    "title",
    "agent",
    "session",
    "shell",
    "label",
    "label_template",
    "resume_mode",
    "resume_template",
    "create_mode",
    "create_template",
    "label_mode",
    "rename_template",
}
WINDOW_FIELDS = {
    "name",
    "agent",
    "command",
    "cwd",
    "env",
    "remote",
    "session",
    "shell",
    "label",
    "label_template",
    "resume_mode",
    "resume_template",
    "create_mode",
    "create_template",
    "label_mode",
    "rename_template",
}
RUNTIMES = set(RUNTIME_CAPABILITIES)
LAYOUT_BACKENDS = {"tmux", "direct"}
RESUME_MODES = {"none", "flag", "internal"}
CREATE_MODES = {"none", "generated_uuid"}
LABEL_MODES = {"none", "metadata", "internal"}
AGENT_STRING_FIELDS = {
    "command",
    "resume_mode",
    "resume_template",
    "create_mode",
    "create_template",
    "label_template",
    "label_mode",
    "rename_template",
}
OPENER_STRING_FIELDS = {"label", "kind", "command"}
TOP_LEVEL_STRING_FIELDS = {"project", "root", "openWith", "layoutBackend"}
DEFAULTS_STRING_FIELDS = {"shell"}
TAB_STRING_FIELDS = {"name", "layout", "layoutBackend", "opener", "cwd"}
REMOTE_STRING_FIELDS = {"host", "user", "cwd"}
PANE_STRING_FIELDS = {
    "name",
    "layoutBackend",
    "layout",
    "opener",
    "cwd",
    "command",
    "title",
    "agent",
    "session",
    "label",
    "label_template",
    "resume_mode",
    "resume_template",
    "create_mode",
    "create_template",
    "label_mode",
    "rename_template",
}
WINDOW_STRING_FIELDS = {
    "name",
    "agent",
    "command",
    "cwd",
    "session",
    "label",
    "label_template",
    "resume_mode",
    "resume_template",
    "create_mode",
    "create_template",
    "label_mode",
    "rename_template",
}
