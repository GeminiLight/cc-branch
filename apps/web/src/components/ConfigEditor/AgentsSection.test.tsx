import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../../i18n";
import AgentsSection from "./AgentsSection";
import type { AgentConfig } from "./types";

function renderAgentsSection(
  agents: Record<string, AgentConfig> = {},
  onChange = vi.fn(),
) {
  render(
    <I18nProvider>
      <AgentsSection
        agents={agents}
        onChange={onChange}
        expanded
        onToggle={vi.fn()}
      />
    </I18nProvider>
  );
  return onChange;
}

describe("AgentsSection", () => {
  it("creates default agent templates with backend-compatible placeholders", () => {
    const onChange = renderAgentsSection();

    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(onChange).toHaveBeenCalledWith({
      "agent-1": expect.objectContaining({
        create_template: "agent-1 --session-id {session_id}",
        label_template: "{project}/{tab}/{pane}",
      }),
    });
  });
});
