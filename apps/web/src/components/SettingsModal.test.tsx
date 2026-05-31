import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import SettingsModal from "./SettingsModal";
import { I18nProvider } from "../i18n";
import { ThemeProvider } from "../theme/ThemeProvider";

vi.mock("./GlobalAgentsSettings", () => ({
  default: () => <div>Global agents panel</div>,
}));

vi.mock("./GlobalOpenersSettings", () => ({
  default: () => <div>Global openers panel</div>,
}));

vi.mock("./DesktopUpdateSettings", () => ({
  default: () => <div>Desktop updates panel</div>,
}));

vi.mock("./DataLocationsSettings", () => ({
  default: () => <div>Data locations panel</div>,
}));

function renderSettings() {
  return render(
    <I18nProvider>
      <ThemeProvider>
        <SettingsModal isOpen onClose={() => {}} />
      </ThemeProvider>
    </I18nProvider>
  );
}

describe("SettingsModal", () => {
  it("keeps settings copy terse and puts maintenance at the bottom", () => {
    renderSettings();

    expect(screen.queryByText("Adjust local app preferences.")).not.toBeInTheDocument();
    expect(screen.queryByText("Theme and language preferences.")).not.toBeInTheDocument();
    expect(screen.queryByText("Updates, paths, and runtime details.")).not.toBeInTheDocument();

    const nav = screen.getByRole("navigation", { name: "Settings sections" });
    const items = within(nav).getAllByRole("button").map((button) => button.textContent);
    expect(items).toEqual(["Appearance", "Templates", "Openers", "Agents", "Maintenance"]);
  });

  it("opens the template center from settings", () => {
    renderSettings();

    fireEvent.click(screen.getByRole("button", { name: "Templates" }));

    expect(screen.getByRole("heading", { name: "Templates" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add template" })).toBeInTheDocument();
  });

  it("opens the openers panel from settings", () => {
    renderSettings();

    fireEvent.click(screen.getByRole("button", { name: "Openers" }));

    expect(screen.getByRole("heading", { name: "Openers" })).toBeInTheDocument();
    expect(screen.getByText("Global openers panel")).toBeInTheDocument();
  });
});
