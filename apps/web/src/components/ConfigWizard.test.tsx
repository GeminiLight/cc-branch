import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import ConfigWizard from "./ConfigWizard";
import { I18nProvider } from "../i18n";
import { ToastProvider } from "./ui/Toast";
import { cloneTemplate, saveUserTemplates, templateSpecs } from "./config-wizard-model";

const mocks = vi.hoisted(() => ({
  saveConfigMutateAsync: vi.fn(),
}));

vi.mock("../hooks", () => ({
  useProfiles: () => ({
    data: [
      { id: "development", description: "One tab for frontend, backend, algorithm, and docs work." },
      { id: "research", description: "Idea and paper work, plus code and experiment panes." },
      { id: "minimal", description: "One tab, one agent pane." },
    ],
  }),
  useAgents: () => ({
    data: { agents: [{ id: "codex" }, { id: "claude" }] },
  }),
  useSaveConfig: () => ({
    mutateAsync: mocks.saveConfigMutateAsync,
    isPending: false,
  }),
}));

function renderWizard() {
  return render(
    <I18nProvider>
      <ToastProvider>
        <ConfigWizard
          isOpen
          projectPath="/tmp/research"
          onClose={vi.fn()}
          onCreated={vi.fn()}
        />
      </ToastProvider>
    </I18nProvider>
  );
}

describe("ConfigWizard", () => {
  beforeEach(() => {
    localStorage.clear();
    mocks.saveConfigMutateAsync.mockReset();
    mocks.saveConfigMutateAsync.mockResolvedValue({ success: true });
  });

  it("lists custom templates in the create flow without small template descriptions", () => {
    saveUserTemplates([
      {
        ...cloneTemplate(templateSpecs.minimal),
        id: "custom-review-loop",
        name: "Review loop",
      },
    ]);

    renderWizard();

    expect(screen.getByRole("button", { name: /Review loop/ })).toBeInTheDocument();
    expect(screen.queryByText("One tab for frontend, backend, algorithm, and docs work.")).not.toBeInTheDocument();
    expect(screen.queryByText("Idea and paper work, plus code and experiment panes.")).not.toBeInTheDocument();
    expect(screen.queryByText("One tab, one agent pane.")).not.toBeInTheDocument();
    expect(screen.getAllByLabelText("Workspace shape").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tab").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Pane").length).toBeGreaterThan(0);
  });

  it("creates config from a selected custom template", async () => {
    saveUserTemplates([
      {
        ...cloneTemplate(templateSpecs.minimal),
        id: "custom-review-loop",
        name: "Review loop",
      },
    ]);

    renderWizard();
    fireEvent.click(screen.getByRole("button", { name: /Review loop/ }));
    fireEvent.click(screen.getByRole("button", { name: "Create workspace" }));

    await waitFor(() => {
      expect(mocks.saveConfigMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          content: expect.stringContaining("name: agent"),
          scope: expect.objectContaining({ projectPath: "/tmp/research" }),
        })
      );
    });
  });

  it("uses saved overrides for default templates", () => {
    const development = cloneTemplate(templateSpecs.development);
    development.tabs[0].panes[0].name = "ui";
    saveUserTemplates([{ ...development, id: "development" }]);

    renderWizard();

    expect(screen.getByDisplayValue("ui")).toBeInTheDocument();
  });
});
