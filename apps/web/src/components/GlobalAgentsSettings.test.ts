import { describe, expect, it } from "vitest";
import {
  removeOrResetAgent,
  serializeGlobalAgents,
  type GlobalAgentConfig,
} from "./GlobalAgentsSettings";

function agent(patch: Partial<GlobalAgentConfig> = {}): GlobalAgentConfig {
  return {
    command: "codex",
    install_hint: "",
    resume_mode: "none",
    resume_template: "",
    create_mode: "none",
    create_template: "",
    label_template: "{project}/{tab}/{pane}",
    label_mode: "metadata",
    rename_template: "",
    ...patch,
  };
}

describe("global agent settings serialization", () => {
  it("does not write unchanged built-in agents into the user override file", () => {
    expect(serializeGlobalAgents({ codex: agent() }, { codex: agent() })).toBe("agents: {}\n");
  });

  it("writes only agents that differ from the built-in baseline", () => {
    const yaml = serializeGlobalAgents(
      {
        codex: agent({ resume_mode: "flag", resume_template: "resume {session_id}" }),
        claude: agent({ command: "claude" }),
      },
      {
        codex: agent(),
        claude: agent({ command: "claude" }),
      },
    );

    expect(yaml).toContain("codex:");
    expect(yaml).toContain("resume_mode: flag");
    expect(yaml).not.toContain("claude:");
  });

  it("keeps empty-string overrides when users clear a built-in field", () => {
    const yaml = serializeGlobalAgents(
      {
        codex: agent({ label_template: "" }),
      },
      {
        codex: agent({ label_template: "{project}/{tab}/{pane}" }),
      },
    );

    expect(yaml).toContain("codex:");
    expect(yaml).toContain("label_template: ''");
  });

  it("keeps custom agents that are not part of the built-in baseline", () => {
    const yaml = serializeGlobalAgents(
      { custom: agent({ command: "my-agent", install_hint: "Install locally" }) },
      {},
    );

    expect(yaml).toContain("custom:");
    expect(yaml).toContain("command: my-agent");
    expect(yaml).toContain("install_hint: Install locally");
  });

  it("resets built-in agents instead of pretending they can be deleted", () => {
    const baseline = { codex: agent() };
    const current = { codex: agent({ resume_mode: "flag" }) };

    expect(removeOrResetAgent(current, baseline, "codex")).toEqual(baseline);
  });

  it("removes custom agents that are not backed by a built-in baseline", () => {
    expect(removeOrResetAgent({ custom: agent({ command: "my-agent" }) }, {}, "custom")).toEqual({});
  });
});
