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
    "default_opener",
    "openWith",
    "layoutBackend",
    "defaults",
    "slots",
    "tabs",
}
DISPLAY_FIELDS = {"mode", "columns", "dashboard"}
DEFAULTS_FIELDS = {"shell"}
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
SLOT_FIELDS = {
    "name",
    "runtime",
    "opener",
    "cwd",
    "env",
    "windows",
    "command",
    "title",
    "agent",
    "session",
    "session_id",
    "label",
}
TAB_FIELDS = {"name", "layout", "layoutBackend", "opener", "cwd", "env", "panes"}
PANE_FIELDS = {
    "name",
    "runtime",
    "layoutBackend",
    "layout",
    "opener",
    "cwd",
    "env",
    "windows",
    "command",
    "title",
    "agent",
    "session",
    "session_id",
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
    "session",
    "session_id",
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
TOP_LEVEL_STRING_FIELDS = {"project", "root", "default_opener", "openWith", "layoutBackend"}
DEFAULTS_STRING_FIELDS = {"shell"}
SLOT_STRING_FIELDS = {"name", "runtime", "opener", "cwd", "command", "title", "agent", "session", "session_id", "label"}
TAB_STRING_FIELDS = {"name", "layout", "layoutBackend", "opener", "cwd"}
PANE_STRING_FIELDS = {
    "name",
    "runtime",
    "layoutBackend",
    "layout",
    "opener",
    "cwd",
    "command",
    "title",
    "agent",
    "session",
    "session_id",
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
WINDOW_STRING_FIELDS = {
    "name",
    "agent",
    "command",
    "cwd",
    "session",
    "session_id",
    "label",
    "label_template",
    "resume_mode",
    "resume_template",
    "create_mode",
    "create_template",
    "label_mode",
    "rename_template",
}
