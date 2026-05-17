import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { APIClient } from "../api/client";
import { I18nProvider } from "../i18n";
import GlobalAgentsSettings from "./GlobalAgentsSettings";
import { ToastProvider } from "./ui/Toast";

function renderSettings(api: APIClient) {
  return render(
    <I18nProvider>
      <ToastProvider>
        <GlobalAgentsSettings api={api} />
      </ToastProvider>
    </I18nProvider>,
  );
}

describe("GlobalAgentsSettings UI", () => {
  it("locks built-in agent names because they are stable IDs", async () => {
    const api = {
      getGlobalAgents: vi.fn().mockResolvedValue({
        path: "/tmp/home/.cc-branch/agents.yaml",
        exists: false,
        content: "agents: {}\n",
        agents: [{
          id: "codex",
          command: "codex",
          install_hint: "",
          resume_mode: "none",
          resume_template: "",
          create_mode: "none",
          create_template: "",
          label_template: "{project}/{tab}/{pane}",
          label_mode: "metadata",
          rename_template: "",
        }],
        builtin_agents: [{
          id: "codex",
          command: "codex",
          install_hint: "",
          resume_mode: "none",
          resume_template: "",
          create_mode: "none",
          create_template: "",
          label_template: "{project}/{tab}/{pane}",
          label_mode: "metadata",
          rename_template: "",
        }],
      }),
    } as unknown as APIClient;

    renderSettings(api);

    const codexInputs = await screen.findAllByDisplayValue("codex");
    expect(codexInputs[0]).toBeDisabled();
    expect(screen.getByText("Built-in agent names are fixed. Edit the command or session behavior instead.")).toBeInTheDocument();
  });
});
