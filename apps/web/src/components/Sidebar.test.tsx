import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { APIClient } from "../api/client";
import { I18nProvider } from "../i18n";
import Sidebar from "./Sidebar";

function renderSidebar(onOpenSettings = vi.fn()) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  const api = {
    getStatus: vi.fn(),
  } as unknown as APIClient;

  render(
    <QueryClientProvider client={client}>
      <I18nProvider>
        <Sidebar
          api={api}
          projects={[]}
          activeProjectId={null}
          onSelectProject={() => {}}
          onAddProject={() => {}}
          onOpenSettings={onOpenSettings}
        />
      </I18nProvider>
    </QueryClientProvider>
  );

  return { onOpenSettings };
}

describe("Sidebar", () => {
  it("opens settings from the footer button", () => {
    window.localStorage.clear();
    const { onOpenSettings } = renderSidebar();

    fireEvent.click(screen.getByRole("button", { name: "Settings" }));

    expect(onOpenSettings).toHaveBeenCalledTimes(1);
  });
});
