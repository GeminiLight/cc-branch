import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { APIClient } from "../api/client";
import { I18nProvider } from "../i18n";
import GlobalOpenersSettings from "./GlobalOpenersSettings";
import { ToastProvider } from "./ui/Toast";

function renderSettings(api: APIClient) {
  return render(
    <I18nProvider>
      <ToastProvider>
        <GlobalOpenersSettings api={api} />
      </ToastProvider>
    </I18nProvider>,
  );
}

describe("GlobalOpenersSettings UI", () => {
  it("adds a user-level terminal opener and saves YAML", async () => {
    const api = {
      getGlobalOpeners: vi.fn().mockResolvedValue({
        path: "/tmp/home/.cc-branch/openers.yaml",
        exists: false,
        content: "openers: {}\n",
        openers: [],
        user_openers: [],
        mtime: null,
        content_hash: "sha256:empty",
      }),
      saveGlobalOpeners: vi.fn().mockResolvedValue({
        success: true,
        path: "/tmp/home/.cc-branch/openers.yaml",
        exists: true,
        content: "openers:\n  ghostty:\n    command: ghostty\n",
        openers: [{ id: "ghostty", label: "Ghostty", kind: "terminal", available: true, capabilities: [], source: "user", executable: "/opt/homebrew/bin/ghostty" }],
        user_openers: [{ id: "ghostty", label: "Ghostty", kind: "terminal", command: "ghostty", args: [], capabilities: [] }],
        mtime: 1,
        content_hash: "sha256:saved",
      }),
    } as unknown as APIClient;

    renderSettings(api);

    await screen.findByText("/tmp/home/.cc-branch/openers.yaml");
    fireEvent.click(screen.getByRole("button", { name: "Add opener" }));
    fireEvent.change(screen.getByLabelText("Opener ID"), { target: { value: "ghostty" } });
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Ghostty" } });
    fireEvent.change(screen.getByLabelText("Command"), { target: { value: "ghostty" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(api.saveGlobalOpeners).toHaveBeenCalledWith(
        expect.stringContaining("ghostty:"),
        null,
        "sha256:empty",
      );
    });
    expect(api.saveGlobalOpeners).toHaveBeenCalledWith(
      expect.stringContaining("command: ghostty"),
      null,
      "sha256:empty",
    );
  });
});
