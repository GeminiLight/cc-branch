import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../../i18n";
import type { AgentWorktreeStatus } from "../../types";
import type { SlotConfig, WindowConfig } from "./types";
import { TerminalPaneEditor } from "./WorkspaceDetailEditors";

function slotFixture(): SlotConfig {
  return {
    name: "dev",
    runtime: "tmux",
    cwd: ".",
    env: {},
    remote: null,
    windows: [],
    agent: "codex",
    command: undefined,
    session: "auto",
  };
}

function windowFixture(): WindowConfig {
  return {
    name: "planner",
    agent: "codex",
    command: null,
    cwd: null,
    env: {},
    remote: null,
    session: "auto",
    shell: null,
    label: null,
    label_template: null,
    resume_mode: null,
    resume_template: null,
    create_mode: null,
    create_template: null,
    label_mode: null,
    rename_template: null,
  };
}

describe("WorkspaceDetailEditors", () => {
  it("lets an agent pane choose a detected worktree as its working directory", () => {
    const onWindowChange = vi.fn();
    const worktrees: AgentWorktreeStatus[] = [
      {
        target: "dev:planner",
        path: "/tmp/demo-planner",
        branch: "cc-branch/dev-planner",
        dirty: true,
        changed_files: 2,
      },
    ];
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <I18nProvider>
          <TerminalPaneEditor
            slot={slotFixture()}
            window={windowFixture()}
            agentOptions={[{ value: "codex", label: "codex" }]}
            worktrees={worktrees}
            onSlotChange={vi.fn()}
            onWindowChange={onWindowChange}
          />
        </I18nProvider>
      </QueryClientProvider>
    );

    fireEvent.change(screen.getByLabelText("Agent worktree"), { target: { value: "/tmp/demo-planner" } });

    expect(screen.getAllByText("cc-branch/dev-planner").length).toBeGreaterThan(0);
    expect(screen.getByText("2 changed")).toBeInTheDocument();
    expect(onWindowChange).toHaveBeenCalledWith({ cwd: "/tmp/demo-planner" });
  });
});
