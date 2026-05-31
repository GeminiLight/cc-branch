import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { I18nProvider } from "../../i18n";
import SessionInput from "./SessionInput";

vi.mock("../../hooks", () => ({
  useAgentSessions: () => ({ data: { sessions: [] }, isFetching: false }),
}));

describe("SessionInput", () => {
  it("explains each session mode before the user has to choose one", () => {
    const onChange = vi.fn();

    render(
      <I18nProvider>
        <SessionInput value="auto" onChange={onChange} agent="codex" />
      </I18nProvider>
    );

    expect(screen.getByText("Auto")).toBeInTheDocument();
    expect(screen.getByText("Fresh")).toBeInTheDocument();
    expect(screen.getByText("Resume")).toBeInTheDocument();
    expect(screen.getByText("Resume the remembered session, or create and remember one when none exists.")).toBeInTheDocument();
    expect(screen.getByText("Always start a clean agent session for this pane.")).toBeInTheDocument();
    expect(screen.getByText("Pick a known session or paste a session id.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Resume/ }));

    expect(onChange).not.toHaveBeenCalledWith("fresh");
    expect(screen.getByPlaceholderText("Codex session ID")).toBeInTheDocument();
  });
});
