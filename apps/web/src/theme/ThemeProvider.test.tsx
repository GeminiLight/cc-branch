import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider, useTheme } from "./ThemeProvider";

function TestTheme() {
  const { theme, toggle } = useTheme();
  return (
    <button type="button" onClick={toggle}>
      <span data-testid="theme">{theme}</span>
    </button>
  );
}

function installMatchMedia(matches = false) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: vi.fn().mockReturnValue({
      matches,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }),
  });
}

describe("ThemeProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.className = "";
    document.documentElement.style.colorScheme = "";
    installMatchMedia(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses a stored theme before falling back to the system theme", async () => {
    localStorage.setItem("cc-branch-theme", "dark");

    render(
      <ThemeProvider>
        <TestTheme />
      </ThemeProvider>
    );

    expect(screen.getByTestId("theme")).toHaveTextContent("dark");
    await waitFor(() => {
      expect(document.documentElement).toHaveClass("dark");
    });
  });

  it("does not crash when storage is unavailable during initialization", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("storage blocked");
    });

    render(
      <ThemeProvider>
        <TestTheme />
      </ThemeProvider>
    );

    expect(screen.getByTestId("theme")).toHaveTextContent("light");
  });

  it("still toggles theme when storage writes fail", async () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("storage blocked");
    });

    render(
      <ThemeProvider>
        <TestTheme />
      </ThemeProvider>
    );

    fireEvent.click(screen.getByRole("button"));

    expect(screen.getByTestId("theme")).toHaveTextContent("dark");
    await waitFor(() => {
      expect(document.documentElement).toHaveClass("dark");
    });
  });
});
