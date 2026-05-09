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
    "slots",
}
DISPLAY_FIELDS = {"mode", "columns", "dashboard"}
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
    "session_id",
    "label",
}
WINDOW_FIELDS = {
    "name",
    "agent",
    "command",
    "cwd",
    "env",
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
RESUME_MODES = {"none", "flag", "command"}
CREATE_MODES = {"none", "generated_uuid"}
LABEL_MODES = {"none", "metadata", "command"}
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
SLOT_STRING_FIELDS = {"name", "runtime", "opener", "cwd", "command", "title", "agent", "session_id", "label"}
WINDOW_STRING_FIELDS = {
    "name",
    "agent",
    "command",
    "cwd",
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
