import { beforeEach, describe, expect, it } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { I18nProvider } from "../i18n";
import TemplateCenterSettings from "./TemplateCenterSettings";
import { loadUserTemplates } from "./config-wizard-model";

function renderTemplateCenter() {
  return render(
    <I18nProvider>
      <TemplateCenterSettings />
    </I18nProvider>
  );
}

describe("TemplateCenterSettings", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("adds a custom template through an editable draft", () => {
    renderTemplateCenter();

    fireEvent.click(screen.getByRole("button", { name: "Add template" }));
    fireEvent.change(screen.getByLabelText("Template name"), { target: { value: "Review loop" } });
    fireEvent.click(screen.getByRole("button", { name: "Save template" }));

    expect(screen.getByText("Review loop")).toBeInTheDocument();
    const saved = loadUserTemplates();
    expect(saved).toHaveLength(1);
    expect(saved[0].id).toBe("custom-review-loop");
    expect(saved[0].name).toBe("Review loop");
  });

  it("saves an override when editing a default template", () => {
    renderTemplateCenter();

    fireEvent.click(screen.getByRole("button", { name: "Edit Development" }));
    const editor = screen.getByRole("region", { name: "Template editor" });
    fireEvent.change(within(editor).getAllByLabelText("Pane name")[0], { target: { value: "ui" } });
    fireEvent.click(screen.getByRole("button", { name: "Save template" }));

    const saved = loadUserTemplates();
    expect(saved).toHaveLength(1);
    expect(saved[0].id).toBe("development");
    expect(saved[0].tabs[0].panes[0].name).toBe("ui");
    expect(screen.getByRole("button", { name: "Reset Development" })).toBeInTheDocument();
  });

  it("lets a template pane choose its Agent CLI, including OpenCode", () => {
    renderTemplateCenter();

    fireEvent.click(screen.getByRole("button", { name: "Edit Development" }));
    const editor = screen.getByRole("region", { name: "Template editor" });
    fireEvent.click(within(editor).getAllByLabelText("Agent CLI")[0]);
    fireEvent.click(screen.getByRole("option", { name: "opencode" }));
    fireEvent.click(screen.getByRole("button", { name: "Save template" }));

    const saved = loadUserTemplates();
    expect(saved[0].id).toBe("development");
    expect(saved[0].tabs[0].panes[0].agent).toBe("opencode");
  });
});
